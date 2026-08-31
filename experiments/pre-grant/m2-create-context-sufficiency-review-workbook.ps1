param(
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private',
    [string]$OutputPath = 'C:\DefensiveDrift\M2-Review\Defensive-Drift-M2-Context-Sufficiency-Review.xlsx',
    [string]$ExpectedPrivateHead = '0c3df389b37ea948129c801276a844ecf3430b9e'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-ExcelColor {
    param(
        [int]$R,
        [int]$G,
        [int]$B
    )
    return ($R + (256 * $G) + (65536 * $B))
}

$ContextRoot = Join-Path $PrivateRepo 'adjudication-working\context-evidence'
$ReviewCsv = Join-Path $ContextRoot 'context-sufficiency-review.csv'
$ContextMapCsv = Join-Path $ContextRoot 'case-context-map.csv'
$OutputDirectory = Split-Path -Parent $OutputPath

Write-Host ('=' * 76)
Write-Host ' DEFENSIVE DRIFT — M2 CONTEXT-SUFFICIENCY REVIEW WORKBOOK'
Write-Host ('=' * 76)

if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) {
    throw "Private repository missing: $PrivateRepo"
}

$PrivateHead = (git -C $PrivateRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve private repository HEAD.'
}
if ($PrivateHead -ne $ExpectedPrivateHead) {
    throw "Unexpected private checkpoint. Expected=$ExpectedPrivateHead Actual=$PrivateHead"
}

$PrivateDirty = @(git -C $PrivateRepo status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect private repository state.'
}
if ($PrivateDirty.Count -gt 0) {
    $PrivateDirty | ForEach-Object { Write-Host "  $_" }
    throw 'Private repository is dirty. Workbook creation stopped.'
}

foreach ($Required in @($ReviewCsv, $ContextMapCsv)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Required input missing: $Required"
    }
}

$ReviewRows = @(Import-Csv -LiteralPath $ReviewCsv)
$ContextRows = @(Import-Csv -LiteralPath $ContextMapCsv)

if ($ReviewRows.Count -ne 100) {
    throw "Expected 100 review rows; found $($ReviewRows.Count)."
}
if ($ContextRows.Count -ne 1952) {
    throw "Expected 1,952 context rows; found $($ContextRows.Count)."
}
if (@($ReviewRows | Where-Object { $_.context_sufficiency -ne 'NOT_REVIEWED' }).Count -ne 0) {
    throw 'Context-sufficiency decisions already exist in the source worklist.'
}
if (@($ReviewRows | Where-Object { $_.ground_truth_assigned -ne 'NO' }).Count -ne 0) {
    throw 'Ground truth is already assigned in the review worklist.'
}
if (@($ContextRows | Where-Object { $_.ground_truth_assigned -ne 'NO' }).Count -ne 0) {
    throw 'Ground truth is already assigned in the context map.'
}

$CaseIds = @($ReviewRows | ForEach-Object { [int]$_.case_index })
if (@($CaseIds | Sort-Object -Unique).Count -ne 100) {
    throw 'Review worklist does not contain 100 unique case indices.'
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
if (Test-Path -LiteralPath $OutputPath) {
    throw "Workbook already exists. Preserve or remove it before rerunning: $OutputPath"
}

$Excel = $null
$Workbook = $null
$SummarySheet = $null
$ReviewSheet = $null
$ContextSheet = $null

try {
    $Excel = New-Object -ComObject Excel.Application
    $Excel.Visible = $false
    $Excel.DisplayAlerts = $false
    $Excel.ScreenUpdating = $false

    $Workbook = $Excel.Workbooks.Add()
    while ($Workbook.Worksheets.Count -lt 3) {
        $null = $Workbook.Worksheets.Add()
    }
    while ($Workbook.Worksheets.Count -gt 3) {
        $Workbook.Worksheets.Item($Workbook.Worksheets.Count).Delete()
    }

    $SummarySheet = $Workbook.Worksheets.Item(1)
    $ReviewSheet = $Workbook.Worksheets.Item(2)
    $ContextSheet = $Workbook.Worksheets.Item(3)
    $SummarySheet.Name = 'Summary'
    $ReviewSheet.Name = 'Review'
    $ContextSheet.Name = 'ContextEvidence'

    $HeaderColor = Get-ExcelColor -R 31 -G 78 -B 121
    $HeaderFontColor = Get-ExcelColor -R 255 -G 255 -B 255
    $AccentColor = Get-ExcelColor -R 221 -G 235 -B 247
    $WarningColor = Get-ExcelColor -R 255 -G 242 -B 204

    Write-Host '[1/4] Building 1,952-row historical-context evidence sheet...'

    $ContextHeaders = @(
        'Case',
        'Rank',
        'Context Candidate',
        'Title',
        'Temporal Relation',
        'Retrieval Score',
        'Retrieval Reasons',
        'Source Repository',
        'Source Path',
        'Source Model',
        'Template Family',
        'Historical Evidence',
        'Ground Truth Assigned'
    )

    for ($Column = 1; $Column -le $ContextHeaders.Count; $Column++) {
        $ContextSheet.Cells.Item(1, $Column).Value2 = $ContextHeaders[$Column - 1]
    }

    $FirstContextRowByCase = @{}
    $ExcelRow = 2

    foreach ($Row in $ContextRows) {
        $CaseIndex = [int]$Row.case_index
        if (-not $FirstContextRowByCase.ContainsKey($CaseIndex)) {
            $FirstContextRowByCase[$CaseIndex] = $ExcelRow
        }

        $ContextSheet.Cells.Item($ExcelRow, 1).Value2 = $CaseIndex
        $ContextSheet.Cells.Item($ExcelRow, 2).Value2 = [int]$Row.context_rank
        $ContextSheet.Cells.Item($ExcelRow, 3).Value2 = $Row.context_candidate_id
        $ContextSheet.Cells.Item($ExcelRow, 4).Value2 = $Row.context_title
        $ContextSheet.Cells.Item($ExcelRow, 5).Value2 = $Row.temporal_relation
        $ContextSheet.Cells.Item($ExcelRow, 6).Value2 = [double]$Row.retrieval_score
        $ContextSheet.Cells.Item($ExcelRow, 7).Value2 = $Row.retrieval_reasons
        $ContextSheet.Cells.Item($ExcelRow, 8).Value2 = $Row.context_source_repository
        $ContextSheet.Cells.Item($ExcelRow, 9).Value2 = $Row.context_source_relative_path
        $ContextSheet.Cells.Item($ExcelRow, 10).Value2 = $Row.context_source_model
        $ContextSheet.Cells.Item($ExcelRow, 11).Value2 = $Row.context_template_family
        $ContextSheet.Cells.Item($ExcelRow, 13).Value2 = $Row.ground_truth_assigned

        $RelativeEvidence = $Row.materialized_evidence_relative_path -replace '/', '\'
        $EvidencePath = Join-Path $ContextRoot $RelativeEvidence
        if (-not (Test-Path -LiteralPath $EvidencePath -PathType Leaf)) {
            throw "Historical evidence missing for case $CaseIndex rank $($Row.context_rank): $EvidencePath"
        }

        $EvidenceCell = $ContextSheet.Cells.Item($ExcelRow, 12)
        $null = $ContextSheet.Hyperlinks.Add(
            $EvidenceCell,
            $EvidencePath,
            $null,
            'Open preserved historical evidence',
            'Open Evidence'
        )

        $ExcelRow++
    }

    $ContextLastRow = $ExcelRow - 1
    if ($ContextLastRow -ne 1953) {
        throw "Unexpected final ContextEvidence row: $ContextLastRow"
    }

    Write-Host '[2/4] Building 100-case human review sheet...'

    $ReviewHeaders = @(
        'Case',
        'Packet ID',
        'Current Candidate',
        'Source Repository',
        'Source Path',
        'Current Evidence',
        'Historical Candidates',
        'View Context',
        'Context Sufficiency',
        'Reviewer Notes',
        'Ground Truth Assigned'
    )

    for ($Column = 1; $Column -le $ReviewHeaders.Count; $Column++) {
        $ReviewSheet.Cells.Item(1, $Column).Value2 = $ReviewHeaders[$Column - 1]
    }

    $ReviewExcelRow = 2
    foreach ($Row in $ReviewRows) {
        $CaseIndex = [int]$Row.case_index
        if (-not $FirstContextRowByCase.ContainsKey($CaseIndex)) {
            throw "No historical context rows found for case $CaseIndex."
        }

        $ReviewSheet.Cells.Item($ReviewExcelRow, 1).Value2 = $CaseIndex
        $ReviewSheet.Cells.Item($ReviewExcelRow, 2).Value2 = $Row.packet_id
        $ReviewSheet.Cells.Item($ReviewExcelRow, 3).Value2 = $Row.combined_candidate_id
        $ReviewSheet.Cells.Item($ReviewExcelRow, 4).Value2 = $Row.source_repository
        $ReviewSheet.Cells.Item($ReviewExcelRow, 5).Value2 = $Row.source_relative_path
        $ReviewSheet.Cells.Item($ReviewExcelRow, 7).Value2 = [int]$Row.retrieved_context_candidates
        $ReviewSheet.Cells.Item($ReviewExcelRow, 9).Value2 = ''
        $ReviewSheet.Cells.Item($ReviewExcelRow, 10).Value2 = ''
        $ReviewSheet.Cells.Item($ReviewExcelRow, 11).Value2 = $Row.ground_truth_assigned

        $CurrentEvidence = $Row.observation_evidence_path
        if (-not (Test-Path -LiteralPath $CurrentEvidence -PathType Leaf)) {
            throw "Current observation evidence missing for case $CaseIndex: $CurrentEvidence"
        }

        $CurrentEvidenceCell = $ReviewSheet.Cells.Item($ReviewExcelRow, 6)
        $null = $ReviewSheet.Hyperlinks.Add(
            $CurrentEvidenceCell,
            $CurrentEvidence,
            $null,
            'Open the already-accepted benchmark observation',
            'Open Current'
        )

        $ContextTargetRow = [int]$FirstContextRowByCase[$CaseIndex]
        $ContextCell = $ReviewSheet.Cells.Item($ReviewExcelRow, 8)
        $null = $ReviewSheet.Hyperlinks.Add(
            $ContextCell,
            [string]::Empty,
            "'ContextEvidence'!A$ContextTargetRow",
            "Jump to retrieved historical context for case $CaseIndex",
            'View Context'
        )

        $ReviewExcelRow++
    }

    if (($ReviewExcelRow - 1) -ne 101) {
        throw "Unexpected final Review row: $($ReviewExcelRow - 1)"
    }

    $DecisionRange = $ReviewSheet.Range('I2:I101')
    $DecisionRange.Validation.Delete()
    $DecisionRange.Validation.Add(
        3,
        1,
        1,
        'SUFFICIENT_FOR_ADJUDICATION,MORE_CONTEXT_REQUIRED'
    )
    $DecisionRange.Validation.IgnoreBlank = $true
    $DecisionRange.Validation.InCellDropdown = $true
    $DecisionRange.Validation.ErrorTitle = 'Choose a permitted context-sufficiency decision'
    $DecisionRange.Validation.ErrorMessage = 'Use SUFFICIENT_FOR_ADJUDICATION or MORE_CONTEXT_REQUIRED.'
    $DecisionRange.Validation.ShowError = $true

    Write-Host '[3/4] Building summary and workbook guidance...'

    $SummarySheet.Range('A1:D1').Merge()
    $SummarySheet.Cells.Item(1, 1).Value2 = 'Defensive Drift — M2 Context-Sufficiency Review'
    $SummarySheet.Cells.Item(2, 1).Value2 = 'Total Cases'
    $SummarySheet.Cells.Item(2, 2).Formula = '=COUNTA(Review!$A$2:$A$101)'
    $SummarySheet.Cells.Item(3, 1).Value2 = 'Reviewed'
    $SummarySheet.Cells.Item(3, 2).Formula = '=COUNTIF(Review!$I$2:$I$101,"SUFFICIENT_FOR_ADJUDICATION")+COUNTIF(Review!$I$2:$I$101,"MORE_CONTEXT_REQUIRED")'
    $SummarySheet.Cells.Item(4, 1).Value2 = 'Sufficient for Adjudication'
    $SummarySheet.Cells.Item(4, 2).Formula = '=COUNTIF(Review!$I$2:$I$101,"SUFFICIENT_FOR_ADJUDICATION")'
    $SummarySheet.Cells.Item(5, 1).Value2 = 'More Context Required'
    $SummarySheet.Cells.Item(5, 2).Formula = '=COUNTIF(Review!$I$2:$I$101,"MORE_CONTEXT_REQUIRED")'
    $SummarySheet.Cells.Item(6, 1).Value2 = 'Remaining'
    $SummarySheet.Cells.Item(6, 2).Formula = '=B2-B3'
    $SummarySheet.Cells.Item(7, 1).Value2 = 'Relationship Ground Truth Assigned'
    $SummarySheet.Cells.Item(7, 2).Formula = '=COUNTIF(Review!$K$2:$K$101,"YES")'

    $SummarySheet.Cells.Item(9, 1).Value2 = 'Purpose'
    $SummarySheet.Cells.Item(9, 2).Value2 = 'Decide whether enough historical evidence is present to proceed to relationship adjudication. This does not decide whether the observation is a true drift; suitability screening already established benchmark-observation eligibility.'
    $SummarySheet.Cells.Item(11, 1).Value2 = 'SUFFICIENT_FOR_ADJUDICATION'
    $SummarySheet.Cells.Item(11, 2).Value2 = 'The supplied historical evidence is adequate to make a defensible relationship decision in the next gate.'
    $SummarySheet.Cells.Item(12, 1).Value2 = 'MORE_CONTEXT_REQUIRED'
    $SummarySheet.Cells.Item(12, 2).Value2 = 'The current retrieved history is not adequate; bounded retrieval expansion is required before relationship adjudication.'
    $SummarySheet.Cells.Item(14, 1).Value2 = 'Scientific Boundary'
    $SummarySheet.Cells.Item(14, 2).Value2 = 'Retrieval score, token overlap, repository/model/template affinity, timestamp ordering, and exact-content hints are retrieval aids only. They do not establish DUPLICATE, RECURRENCE, NEW, RELATED_BUT_DISTINCT, or INSUFFICIENT_EVIDENCE.'
    $SummarySheet.Cells.Item(16, 1).Value2 = 'Private Evidence Commit'
    $SummarySheet.Cells.Item(16, 2).Value2 = $ExpectedPrivateHead
    $SummarySheet.Cells.Item(17, 1).Value2 = 'Historical Relationships'
    $SummarySheet.Cells.Item(17, 2).Value2 = 1952
    $SummarySheet.Cells.Item(18, 1).Value2 = 'Unique Historical Evidence Records'
    $SummarySheet.Cells.Item(18, 2).Value2 = 820

    foreach ($Sheet in @($ReviewSheet, $ContextSheet)) {
        $LastColumn = if ($Sheet.Name -eq 'Review') { 11 } else { 13 }
        $LastRow = if ($Sheet.Name -eq 'Review') { 101 } else { 1953 }
        $HeaderRange = $Sheet.Range($Sheet.Cells.Item(1, 1), $Sheet.Cells.Item(1, $LastColumn))
        $HeaderRange.Interior.Color = $HeaderColor
        $HeaderRange.Font.Color = $HeaderFontColor
        $HeaderRange.Font.Bold = $true
        $HeaderRange.WrapText = $true
        $HeaderRange.HorizontalAlignment = -4108
        $HeaderRange.VerticalAlignment = -4108
        $Sheet.Range($Sheet.Cells.Item(1, 1), $Sheet.Cells.Item($LastRow, $LastColumn)).AutoFilter()
    }

    $SummarySheet.Range('A1:D1').Interior.Color = $HeaderColor
    $SummarySheet.Range('A1:D1').Font.Color = $HeaderFontColor
    $SummarySheet.Range('A1:D1').Font.Bold = $true
    $SummarySheet.Range('A1:D1').Font.Size = 14
    $SummarySheet.Range('A2:B7').Borders.LineStyle = 1
    $SummarySheet.Range('A2:A7').Interior.Color = $AccentColor
    $SummarySheet.Range('A11:A12').Interior.Color = $WarningColor
    $SummarySheet.Range('A1:D18').VerticalAlignment = -4160
    $SummarySheet.Range('A1:D18').WrapText = $true

    $ReviewSheet.Range('A1:K101').VerticalAlignment = -4160
    $ReviewSheet.Range('D2:E101').WrapText = $true
    $ReviewSheet.Range('J2:J101').WrapText = $true
    $ReviewSheet.Range('I2:I101').Interior.Color = $WarningColor

    $ContextSheet.Range('A1:M1953').VerticalAlignment = -4160
    $ContextSheet.Range('D2:K1953').WrapText = $true
    $ContextSheet.Range('F2:F1953').NumberFormat = '0.000000'

    $SummarySheet.Columns.Item('A').ColumnWidth = 32
    $SummarySheet.Columns.Item('B').ColumnWidth = 75
    $SummarySheet.Columns.Item('C').ColumnWidth = 2
    $SummarySheet.Columns.Item('D').ColumnWidth = 2

    $ReviewSheet.Columns.Item('A').ColumnWidth = 8
    $ReviewSheet.Columns.Item('B').ColumnWidth = 20
    $ReviewSheet.Columns.Item('C').ColumnWidth = 18
    $ReviewSheet.Columns.Item('D').ColumnWidth = 28
    $ReviewSheet.Columns.Item('E').ColumnWidth = 45
    $ReviewSheet.Columns.Item('F').ColumnWidth = 18
    $ReviewSheet.Columns.Item('G').ColumnWidth = 12
    $ReviewSheet.Columns.Item('H').ColumnWidth = 15
    $ReviewSheet.Columns.Item('I').ColumnWidth = 30
    $ReviewSheet.Columns.Item('J').ColumnWidth = 45
    $ReviewSheet.Columns.Item('K').ColumnWidth = 18

    $ContextSheet.Columns.Item('A').ColumnWidth = 8
    $ContextSheet.Columns.Item('B').ColumnWidth = 8
    $ContextSheet.Columns.Item('C').ColumnWidth = 18
    $ContextSheet.Columns.Item('D').ColumnWidth = 45
    $ContextSheet.Columns.Item('E').ColumnWidth = 16
    $ContextSheet.Columns.Item('F').ColumnWidth = 14
    $ContextSheet.Columns.Item('G').ColumnWidth = 42
    $ContextSheet.Columns.Item('H').ColumnWidth = 28
    $ContextSheet.Columns.Item('I').ColumnWidth = 45
    $ContextSheet.Columns.Item('J').ColumnWidth = 18
    $ContextSheet.Columns.Item('K').ColumnWidth = 20
    $ContextSheet.Columns.Item('L').ColumnWidth = 18
    $ContextSheet.Columns.Item('M').ColumnWidth = 18

    $ReviewSheet.Activate() | Out-Null
    $Excel.ActiveWindow.SplitRow = 1
    $Excel.ActiveWindow.FreezePanes = $true
    $ContextSheet.Activate() | Out-Null
    $Excel.ActiveWindow.SplitRow = 1
    $Excel.ActiveWindow.FreezePanes = $true
    $ReviewSheet.Activate() | Out-Null

    $Excel.CalculateFullRebuild()

    Write-Host '[4/4] Saving and validating workbook...'

    $Workbook.SaveAs($OutputPath, 51)
    $Workbook.Close($true)
    $Workbook = $null

    $CheckWorkbook = $Excel.Workbooks.Open($OutputPath, 0, $true)
    try {
        if ($CheckWorkbook.Worksheets.Count -ne 3) {
            throw "Expected 3 worksheets; found $($CheckWorkbook.Worksheets.Count)."
        }

        foreach ($SheetName in @('Summary', 'Review', 'ContextEvidence')) {
            $null = $CheckWorkbook.Worksheets.Item($SheetName)
        }

        $CheckReview = $CheckWorkbook.Worksheets.Item('Review')
        $CheckContext = $CheckWorkbook.Worksheets.Item('ContextEvidence')
        $CheckSummary = $CheckWorkbook.Worksheets.Item('Summary')

        if ($CheckReview.Hyperlinks.Count -ne 200) {
            throw "Expected 200 Review hyperlinks; found $($CheckReview.Hyperlinks.Count)."
        }
        if ($CheckContext.Hyperlinks.Count -ne 1952) {
            throw "Expected 1,952 ContextEvidence hyperlinks; found $($CheckContext.Hyperlinks.Count)."
        }
        if ([int]$CheckSummary.Cells.Item(2, 2).Value2 -ne 100) {
            throw 'Summary total-case formula did not evaluate to 100.'
        }
        if ([int]$CheckSummary.Cells.Item(3, 2).Value2 -ne 0) {
            throw 'Summary reviewed count should begin at 0.'
        }
        if ([int]$CheckSummary.Cells.Item(6, 2).Value2 -ne 100) {
            throw 'Summary remaining count should begin at 100.'
        }
        if ([int]$CheckSummary.Cells.Item(7, 2).Value2 -ne 0) {
            throw 'Relationship ground-truth count must remain 0.'
        }
    }
    finally {
        $CheckWorkbook.Close($false)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($CheckWorkbook)
    }

    $WorkbookHash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash

    Write-Host ''
    Write-Host ('=' * 76)
    Write-Host ' M2 CONTEXT-SUFFICIENCY WORKBOOK READY'
    Write-Host " Workbook=$OutputPath"
    Write-Host " WorkbookSHA256=$WorkbookHash"
    Write-Host ' Sheets=Summary, Review, ContextEvidence'
    Write-Host ' Cases=100'
    Write-Host ' HistoricalContextRows=1952'
    Write-Host ' CurrentEvidenceHyperlinks=100'
    Write-Host ' ContextJumpHyperlinks=100'
    Write-Host ' HistoricalEvidenceHyperlinks=1952'
    Write-Host ' InitialReviewed=0'
    Write-Host ' InitialRemaining=100'
    Write-Host ' GroundTruthAssigned=0'
    Write-Host ' NEXT=complete all 100 Context Sufficiency decisions and return the workbook'
    Write-Host ('=' * 76)

    Start-Process -FilePath $OutputPath
}
finally {
    if ($Workbook -ne $null) {
        try { $Workbook.Close($false) } catch {}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Workbook)
    }
    if ($SummarySheet -ne $null) {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($SummarySheet)
    }
    if ($ReviewSheet -ne $null) {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ReviewSheet)
    }
    if ($ContextSheet -ne $null) {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ContextSheet)
    }
    if ($Excel -ne $null) {
        try { $Excel.Quit() } catch {}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Excel)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
