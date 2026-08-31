param(
    [string]$PublicRepo = 'C:\GitHub\openai-defensive-drift',
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private',
    [string]$OutputPath = 'C:\DefensiveDrift\M2-Review\Defensive-Drift-M2-Context-Sufficiency-Review.xlsx',
    [string]$ExpectedPrivateHead = '0c3df389b37ea948129c801276a844ecf3430b9e'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RelativeBuilder = 'experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1'
$ExpectedBuilderBlob = '2a6e58bdcc36ba7cc4288e371f73351b5f36456d'
$Builder = Join-Path $PublicRepo $RelativeBuilder
$TempScript = Join-Path ([IO.Path]::GetTempPath()) ("m2-context-sufficiency-workbook-repaired-$([guid]::NewGuid().ToString('N')).ps1")

Write-Host ('=' * 76)
Write-Host ' DEFENSIVE DRIFT — M2 CONTEXT-SUFFICIENCY WORKBOOK PARSER REPAIR'
Write-Host ('=' * 76)

if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
    throw "Canonical workbook builder missing: $Builder"
}

$ActualBuilderBlob = (git -C $PublicRepo rev-parse "HEAD:$RelativeBuilder").Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve canonical workbook-builder blob.'
}
if ($ActualBuilderBlob -ne $ExpectedBuilderBlob) {
    throw "Canonical builder changed. Expected=$ExpectedBuilderBlob Actual=$ActualBuilderBlob"
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
    throw 'Private repository is dirty. Workbook repair execution stopped.'
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "Workbook already exists. Preserve or remove it before rerunning: $OutputPath"
}

$SourceText = Get-Content -LiteralPath $Builder -Raw -Encoding UTF8
$BrokenToken = '$CaseIndex:'
$FixedToken = '${CaseIndex}:'
$OccurrenceCount = ([regex]::Matches($SourceText, [regex]::Escape($BrokenToken))).Count

if ($OccurrenceCount -ne 1) {
    throw "Expected exactly one invalid '$BrokenToken' token; found $OccurrenceCount. Refusing broad repair."
}

$RepairedText = $SourceText.Replace($BrokenToken, $FixedToken)

try {
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($TempScript, $RepairedText, $Utf8NoBom)

    $Tokens = $null
    $ParseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $TempScript,
        [ref]$Tokens,
        [ref]$ParseErrors
    ) | Out-Null

    if (@($ParseErrors).Count -gt 0) {
        $ParseErrors | ForEach-Object {
            Write-Host ("  Line {0}: {1}" -f $_.Extent.StartLineNumber, $_.Message)
        }
        throw 'Repaired workbook builder still fails PowerShell parser validation.'
    }

    Write-Host "CanonicalBuilderBlob=PASS — $ActualBuilderBlob"
    Write-Host 'RepairScope=PASS — exactly one $CaseIndex: -> ${CaseIndex}: replacement'
    Write-Host 'RepairedParser=PASS'
    Write-Host "PrivateCheckpoint=PASS — $PrivateHead"
    Write-Host ''
    Write-Host '[execute repaired workbook builder]'

    & $TempScript `
        -PrivateRepo $PrivateRepo `
        -OutputPath $OutputPath `
        -ExpectedPrivateHead $ExpectedPrivateHead

    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "Expected workbook was not created: $OutputPath"
    }

    $WorkbookHash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash

    Write-Host ''
    Write-Host ('=' * 76)
    Write-Host ' M2 CONTEXT-SUFFICIENCY WORKBOOK RECOVERY COMPLETE'
    Write-Host " Workbook=$OutputPath"
    Write-Host " WorkbookSHA256=$WorkbookHash"
    Write-Host ' ReviewCases=100'
    Write-Host ' GroundTruthAssigned=0'
    Write-Host ' NEXT=complete all 100 Context Sufficiency decisions and upload the saved workbook'
    Write-Host ('=' * 76)
}
finally {
    if (Test-Path -LiteralPath $TempScript) {
        Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
    }
}