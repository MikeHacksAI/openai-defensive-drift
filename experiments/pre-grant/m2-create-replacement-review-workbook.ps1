param(
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private',
    [string]$OutputPath = 'C:\DefensiveDrift\M2-Review\Defensive-Drift-M2-Replacement-Suitability-Review.xlsx',
    [string]$ExpectedPrivateHead = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ReviewSet = Join-Path $PrivateRepo 'adjudication-working\replacement-review\replacement-review-set.csv'
$ReplacementRoot = Join-Path $PrivateRepo 'adjudication-working\replacement-review'
$OutputDir = Split-Path -Parent $OutputPath
$TempPath = Join-Path $OutputDir 'Defensive-Drift-M2-Replacement-Suitability-Review.__building__.xlsx'

Write-Host '============================================================================'
Write-Host ' DEFENSIVE DRIFT — M2 22-CASE REPLACEMENT SUITABILITY WORKBOOK'
Write-Host " Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
Write-Host '============================================================================'

Write-Host "`n[1/7] Verify private checkpoint and replacement review set..."

if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) {
    throw "Private repository missing: $PrivateRepo"
}

$Dirty = @(git -C $PrivateRepo status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect private repository.'
}
if ($Dirty.Count -gt 0) {
    $Dirty | ForEach-Object { Write-Host "  $_" }
    throw 'Private repository is dirty. Workbook build NOT started.'
}

$PrivateHead = (git -C $PrivateRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve private HEAD.'
}
if (-not [string]::IsNullOrWhiteSpace($ExpectedPrivateHead) -and $PrivateHead -ne $ExpectedPrivateHead) {
    throw "Unexpected private checkpoint. Expected=$ExpectedPrivateHead Actual=$PrivateHead"
}

if (-not (Test-Path -LiteralPath $ReviewSet -PathType Leaf)) {
    throw "Replacement review set missing: $ReviewSet"
}

$Rows = @(Import-Csv -LiteralPath $ReviewSet)
if ($Rows.Count -ne 22) {
    throw "Expected 22 replacement rows; found $($Rows.Count)."
}
if (@($Rows.packet_id | Sort-Object -Unique).Count -ne 22) {
    throw 'Replacement packet IDs are not unique.'
}
if (@($Rows.combined_candidate_id | Sort-Object -Unique).Count -ne 22) {
    throw 'Replacement candidate IDs are not unique.'
}
if (@($Rows | Where-Object { $_.record_suitability -ne 'NOT_REVIEWED' }).Count -ne 0) {
    throw 'Replacement review set already contains suitability decisions.'
}
if (@($Rows | Where-Object { $_.ground_truth_assigned -ne 'NO' }).Count -ne 0) {
    throw 'Ground-truth boundary violation in replacement review set.'
}

$EvidenceMap = @{}
foreach ($Row in $Rows) {
    $Evidence = Join-Path $ReplacementRoot ($Row.evidence_relative_path -replace '/', '\')
    if (-not (Test-Path -LiteralPath $Evidence -PathType Leaf)) {
        throw "Evidence copy missing for $($Row.packet_id): $Evidence"
    }
    $EvidenceMap[$Row.packet_id] = $Evidence
}

Write-Host "  PrivateCheckpoint=PASS — $PrivateHead"
Write-Host '  ReplacementRows=22'
Write-Host '  EvidenceCopiesPresent=22'
Write-Host '  GroundTruthAssigned=0'

Write-Host "`n[2/7] Prepare clean output target..."

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

if (Test-Path -LiteralPath $OutputPath) {
    throw "Final workbook already exists. Refusing to overwrite possible human review work: $OutputPath"
}
if (Test-Path -LiteralPath $TempPath) {
    Remove-Item -LiteralPath $TempPath -Force
}

$Excel = $null
$Workbook = $null
$Reopened = $null
$Review = $null
$Summary = $null
$Review2 = $null
$Summary2 = $null

try {
    Write-Host "`n[3/7] Build workbook with installed Microsoft Excel..."

    $Excel = New-Object -ComObject Excel.Application
    $Excel.Visible = $false
    $Excel.DisplayAlerts = $false
    $Excel.ScreenUpdating = $false

    $Workbook = $Excel.Workbooks.Add()

    while ($Workbook.Worksheets.Count -gt 1) {
        $Workbook.Worksheets.Item($Workbook.Worksheets.Count).Delete()
    }

    $Review = $Workbook.Worksheets.Item(1)
    $Review.Name = 'Review'

    $Summary = $Workbook.Worksheets.Add()
    $Summary.Name = 'Summary'

    $Headers = @(
        'Rank',
        'Packet ID',
        'Reserve Rank',
        'Candidate ID',
        'Repository',
        'Source Relative Path',
        'Model',
        'Template Family',
        'Severity',
        'Recurrence',
        'Selection Reason',
        'Suitability',
        'Rejection Reason',
        'Reviewer Notes',
        'Verified Evidence Path'
    )

    for ($Column = 0; $Column -lt $Headers.Count; $Column++) {
        $Review.Cells.Item(1, $Column + 1).Value2 = $Headers[$Column]
    }

    $Review.Range('B:O').NumberFormat = '@'

    $ExcelRow = 2
    foreach ($Row in $Rows) {
        $Evidence = $EvidenceMap[$Row.packet_id]

        $Review.Cells.Item($ExcelRow, 1).Value2 = [int]$Row.replacement_rank
        $Review.Cells.Item($ExcelRow, 2).Value2 = [string]$Row.packet_id
        $Review.Cells.Item($ExcelRow, 3).Value2 = [string]$Row.reserve_review_rank
        $Review.Cells.Item($ExcelRow, 4).Value2 = [string]$Row.combined_candidate_id
        $Review.Cells.Item($ExcelRow, 5).Value2 = [string]$Row.source_repository

        $Anchor = $Review.Cells.Item($ExcelRow, 6)
        $null = $Review.Hyperlinks.Add(
            $Anchor,
            $Evidence,
            '',
            "Open verified evidence copy for $($Row.packet_id)",
            [string]$Row.source_relative_path
        )

        $Review.Cells.Item($ExcelRow, 7).Value2 = [string]$Row.source_model
        $Review.Cells.Item($ExcelRow, 8).Value2 = [string]$Row.template_family
        $Review.Cells.Item($ExcelRow, 9).Value2 = [string]$Row.severity_bucket
        $Review.Cells.Item($ExcelRow, 10).Value2 = [string]$Row.recurrence_raw
        $Review.Cells.Item($ExcelRow, 11).Value2 = [string]$Row.selection_reasons
        $Review.Cells.Item($ExcelRow, 12).Value2 = ''
        $Review.Cells.Item($ExcelRow, 13).Value2 = ''
        $Review.Cells.Item($ExcelRow, 14).Value2 = ''
        $Review.Cells.Item($ExcelRow, 15).Value2 = $Evidence

        $ExcelRow++
    }

    if ($Review.Hyperlinks.Count -ne 22) {
        throw "Expected 22 evidence hyperlinks; found $($Review.Hyperlinks.Count)."
    }

    Write-Host '  ReviewRowsWritten=22'
    Write-Host '  ColumnFHyperlinksCreated=22'

    Write-Host "`n[4/7] Add review controls and correct summary formulas..."

    $SuitabilityRange = $Review.Range('L2:L23')
    $SuitabilityRange.Validation.Delete()
    $SuitabilityRange.Validation.Add(
        3,
        1,
        1,
        'SUITABLE,UNSUITABLE,NEEDS_MORE_CONTEXT'
    )
    $SuitabilityRange.Validation.IgnoreBlank = $true
    $SuitabilityRange.Validation.InCellDropdown = $true

    $ReasonRange = $Review.Range('M2:M23')
    $ReasonRange.Validation.Delete()
    $ReasonRange.Validation.Add(
        3,
        1,
        1,
        'TEMPLATE_OR_SCHEMA,RUNBOOK_STANDARD_OR_POLICY,PROJECT_ADMIN_HANDOFF_OR_CHECKPOINT,AGGREGATE_CONTAINER_NOT_SINGLE_OBSERVATION,NOT_AN_INCIDENT_OR_OBSERVATION,MIRROR_OR_REDUNDANT_COPY,OTHER'
    )
    $ReasonRange.Validation.IgnoreBlank = $true
    $ReasonRange.Validation.InCellDropdown = $true

    $Header = $Review.Range('A1:O1')
    $Header.Font.Bold = $true
    $Header.Font.Color = 16777215
    $Header.Interior.Color = 7886879

    $Review.Range('A1:O23').AutoFilter()
    $Review.Activate()
    $Excel.ActiveWindow.SplitRow = 1
    $Excel.ActiveWindow.FreezePanes = $true

    $Widths = @{
        'A:A' = 7
        'B:B' = 18
        'C:C' = 12
        'D:D' = 16
        'E:E' = 28
        'F:F' = 55
        'G:G' = 18
        'H:H' = 26
        'I:I' = 12
        'J:J' = 30
        'K:K' = 28
        'L:L' = 23
        'M:M' = 40
        'N:N' = 40
        'O:O' = 70
    }
    foreach ($ColumnName in $Widths.Keys) {
        $Review.Range($ColumnName).ColumnWidth = $Widths[$ColumnName]
    }
    $Review.Range('E:O').WrapText = $true
    $Review.Range('A1:O23').VerticalAlignment = -4160

    $Summary.Cells.Item(1,1).Value2 = 'M2 Replacement Suitability Review'
    $Summary.Cells.Item(1,2).Value2 = 'Count'
    $Summary.Cells.Item(2,1).Value2 = 'Total'
    $Summary.Cells.Item(2,2).Value2 = 22
    $Summary.Cells.Item(3,1).Value2 = 'Reviewed'
    $Summary.Cells.Item(3,2).Formula = '=SUM(B4:B6)'
    $Summary.Cells.Item(4,1).Value2 = 'Suitable'
    $Summary.Cells.Item(4,2).Formula = '=COUNTIF(Review!L2:L23,"SUITABLE")'
    $Summary.Cells.Item(5,1).Value2 = 'Unsuitable'
    $Summary.Cells.Item(5,2).Formula = '=COUNTIF(Review!L2:L23,"UNSUITABLE")'
    $Summary.Cells.Item(6,1).Value2 = 'Needs More Context'
    $Summary.Cells.Item(6,2).Formula = '=COUNTIF(Review!L2:L23,"NEEDS_MORE_CONTEXT")'
    $Summary.Cells.Item(7,1).Value2 = 'Remaining'
    $Summary.Cells.Item(7,2).Formula = '=B2-B3'

    $Summary.Range('A1:B1').Font.Bold = $true
    $Summary.Range('A:A').ColumnWidth = 34
    $Summary.Range('B:B').ColumnWidth = 14
    $Summary.Cells.Item(9,1).Value2 = 'Review workflow'
    $Summary.Cells.Item(10,1).Value2 = '1. Open the Review sheet.'
    $Summary.Cells.Item(11,1).Value2 = '2. Click Source Relative Path in column F.'
    $Summary.Cells.Item(12,1).Value2 = '3. Read the preserved source-record.md evidence copy.'
    $Summary.Cells.Item(13,1).Value2 = '4. Select SUITABLE, UNSUITABLE, or NEEDS_MORE_CONTEXT.'
    $Summary.Cells.Item(14,1).Value2 = '5. If UNSUITABLE, select a rejection reason.'
    $Summary.Cells.Item(15,1).Value2 = '6. Do NOT assign NEW / DUPLICATE / RECURRENCE here.'
    $Summary.Range('A9:A15').ColumnWidth = 82
    $Summary.Range('A9:A15').WrapText = $true

    $Excel.CalculateFull()

    if ([int]$Summary.Range('B2').Value2 -ne 22) { throw 'Fresh Total must equal 22.' }
    if ([int]$Summary.Range('B3').Value2 -ne 0) { throw 'Fresh Reviewed must equal 0.' }
    if ([int]$Summary.Range('B4').Value2 -ne 0) { throw 'Fresh Suitable must equal 0.' }
    if ([int]$Summary.Range('B5').Value2 -ne 0) { throw 'Fresh Unsuitable must equal 0.' }
    if ([int]$Summary.Range('B6').Value2 -ne 0) { throw 'Fresh Needs More Context must equal 0.' }
    if ([int]$Summary.Range('B7').Value2 -ne 22) { throw 'Fresh Remaining must equal 22.' }

    Write-Host '  InitialSummary=PASS'
    Write-Host '  Reviewed=0'
    Write-Host '  Remaining=22'

    Write-Host "`n[5/7] Save temporary XLSX and reopen with Microsoft Excel..."

    $Workbook.SaveAs($TempPath, 51)
    $Workbook.Close($true)
    $Workbook = $null

    if (-not (Test-Path -LiteralPath $TempPath -PathType Leaf)) {
        throw 'Temporary workbook was not created.'
    }

    $Reopened = $Excel.Workbooks.Open($TempPath)
    $Review2 = $Reopened.Worksheets.Item('Review')
    $Summary2 = $Reopened.Worksheets.Item('Summary')
    $Excel.CalculateFull()

    if ($Review2.UsedRange.Rows.Count -ne 23) {
        throw "Excel reopen row validation failed. Expected=23 Actual=$($Review2.UsedRange.Rows.Count)"
    }
    if ($Review2.Hyperlinks.Count -ne 22) {
        throw "Excel reopen hyperlink validation failed. Expected=22 Actual=$($Review2.Hyperlinks.Count)"
    }
    if ($Review2.Range('L2').Validation.Type -ne 3) {
        throw 'Suitability dropdown failed Excel reopen validation.'
    }
    if ($Review2.Range('M2').Validation.Type -ne 3) {
        throw 'Rejection-reason dropdown failed Excel reopen validation.'
    }

    $FirstEvidence = $Review2.Hyperlinks.Item(1).Address
    $LastEvidence = $Review2.Hyperlinks.Item(22).Address
    if (-not (Test-Path -LiteralPath $FirstEvidence -PathType Leaf)) {
        throw "First evidence hyperlink target missing: $FirstEvidence"
    }
    if (-not (Test-Path -LiteralPath $LastEvidence -PathType Leaf)) {
        throw "Last evidence hyperlink target missing: $LastEvidence"
    }

    if ([int]$Summary2.Range('B2').Value2 -ne 22) { throw 'Reopen Total must equal 22.' }
    if ([int]$Summary2.Range('B3').Value2 -ne 0) { throw 'Reopen Reviewed must equal 0.' }
    if ([int]$Summary2.Range('B4').Value2 -ne 0) { throw 'Reopen Suitable must equal 0.' }
    if ([int]$Summary2.Range('B5').Value2 -ne 0) { throw 'Reopen Unsuitable must equal 0.' }
    if ([int]$Summary2.Range('B6').Value2 -ne 0) { throw 'Reopen Needs More Context must equal 0.' }
    if ([int]$Summary2.Range('B7').Value2 -ne 22) { throw 'Reopen Remaining must equal 22.' }

    $Reopened.Close($false)
    $Reopened = $null

    Write-Host '  ExcelReopen=PASS'
    Write-Host '  HyperlinksAfterReopen=22'
    Write-Host '  SuitabilityDropdown=PASS'
    Write-Host '  RejectionDropdown=PASS'
    Write-Host '  SummaryFormulas=PASS'
    Write-Host '  FirstEvidenceTarget=PASS'
    Write-Host '  LastEvidenceTarget=PASS'

    Write-Host "`n[6/7] Promote verified workbook to final path..."

    Move-Item -LiteralPath $TempPath -Destination $OutputPath
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw 'Final workbook promotion failed.'
    }

    Write-Host "  Workbook=$OutputPath"

    Write-Host "`n[7/7] Final status..."
    Write-Host ''
    Write-Host '============================================================================'
    Write-Host ' M2 REPLACEMENT SUITABILITY WORKBOOK READY'
    Write-Host ' ReviewRows=22'
    Write-Host ' EvidenceHyperlinks=22'
    Write-Host ' Reviewed=0'
    Write-Host ' Remaining=22'
    Write-Host ' GroundTruthAssigned=0'
    Write-Host " Workbook=$OutputPath"
    Write-Host ' NEXT=human suitability review of all 22 replacement packets'
    Write-Host '============================================================================'
}
finally {
    if ($null -ne $Reopened) {
        try { $Reopened.Close($false) } catch {}
    }
    if ($null -ne $Workbook) {
        try { $Workbook.Close($false) } catch {}
    }
    if ($null -ne $Excel) {
        try { $Excel.Quit() } catch {}
    }

    foreach ($ComObject in @($Review2, $Summary2, $Review, $Summary, $Reopened, $Workbook, $Excel)) {
        if ($null -ne $ComObject) {
            try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ComObject) } catch {}
        }
    }

    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()

    if (Test-Path -LiteralPath $TempPath) {
        Remove-Item -LiteralPath $TempPath -Force -ErrorAction SilentlyContinue
    }
}

Start-Process -FilePath $OutputPath
