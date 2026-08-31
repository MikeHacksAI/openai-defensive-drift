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
$TempScript = Join-Path ([IO.Path]::GetTempPath()) ("m2-context-sufficiency-workbook-reviewed-$([guid]::NewGuid().ToString('N')).ps1")
$ExecutionStarted = $false
$ExecutionSucceeded = $false

function Get-GitBlobSha1FromBytes {
    param([byte[]]$Bytes)

    $HeaderBytes = [Text.Encoding]::ASCII.GetBytes("blob $($Bytes.Length)`0")
    $Payload = New-Object byte[] ($HeaderBytes.Length + $Bytes.Length)
    [Buffer]::BlockCopy($HeaderBytes, 0, $Payload, 0, $HeaderBytes.Length)
    [Buffer]::BlockCopy($Bytes, 0, $Payload, $HeaderBytes.Length, $Bytes.Length)

    $Sha1 = [Security.Cryptography.SHA1]::Create()
    try {
        $Hash = $Sha1.ComputeHash($Payload)
    }
    finally {
        $Sha1.Dispose()
    }

    return (($Hash | ForEach-Object { $_.ToString('x2') }) -join '')
}

function Replace-ExactlyOnce {
    param(
        [string]$Text,
        [string]$OldValue,
        [string]$NewValue,
        [string]$Label
    )

    $Count = ([regex]::Matches($Text, [regex]::Escape($OldValue))).Count
    if ($Count -ne 1) {
        throw "Patch invariant failed for $Label. Expected exactly one occurrence; found $Count."
    }

    return $Text.Replace($OldValue, $NewValue)
}

Write-Host ('=' * 76)
Write-Host ' DEFENSIVE DRIFT — M2 CONTEXT-SUFFICIENCY WORKBOOK REVIEWED RECOVERY'
Write-Host ('=' * 76)

if (-not (Test-Path -LiteralPath (Join-Path $PublicRepo '.git') -PathType Container)) {
    throw "Public repository missing or invalid: $PublicRepo"
}
if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) {
    throw "Private repository missing or invalid: $PrivateRepo"
}
if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
    throw "Canonical workbook builder missing: $Builder"
}

$PublicDirty = @(git -C $PublicRepo status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect public repository state.'
}
if ($PublicDirty.Count -gt 0) {
    $PublicDirty | ForEach-Object { Write-Host "  $_" }
    throw 'Public repository is dirty. Reviewed recovery stopped.'
}

$ActualBuilderBlob = (git -C $PublicRepo rev-parse "HEAD:$RelativeBuilder").Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve canonical workbook-builder blob.'
}
if ($ActualBuilderBlob -ne $ExpectedBuilderBlob) {
    throw "Canonical builder changed. Expected=$ExpectedBuilderBlob Actual=$ActualBuilderBlob"
}

$BuilderBytes = [IO.File]::ReadAllBytes($Builder)
$ExecutionSourceBlob = Get-GitBlobSha1FromBytes -Bytes $BuilderBytes
if ($ExecutionSourceBlob -ne $ExpectedBuilderBlob) {
    throw "Working-tree builder bytes do not match the reviewed Git blob. Expected=$ExpectedBuilderBlob Actual=$ExecutionSourceBlob"
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
    throw 'Private repository is dirty. Reviewed recovery stopped.'
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "Workbook already exists. Preserve or remove it before rerunning: $OutputPath"
}

$Utf8Strict = New-Object System.Text.UTF8Encoding -ArgumentList $false, $true
$SourceText = $Utf8Strict.GetString($BuilderBytes)

$RepairedText = Replace-ExactlyOnce `
    -Text $SourceText `
    -OldValue '$CaseIndex:' `
    -NewValue '${CaseIndex}:' `
    -Label 'PowerShell variable/colon parser repair'

$RepairedText = Replace-ExactlyOnce `
    -Text $RepairedText `
    -OldValue '$ReviewRows = @(Import-Csv -LiteralPath $ReviewCsv)' `
    -NewValue '$ReviewRows = @(Import-Csv -LiteralPath $ReviewCsv -Encoding UTF8)' `
    -Label 'Review CSV explicit UTF-8 decoding'

$RepairedText = Replace-ExactlyOnce `
    -Text $RepairedText `
    -OldValue '$ContextRows = @(Import-Csv -LiteralPath $ContextMapCsv)' `
    -NewValue '$ContextRows = @(Import-Csv -LiteralPath $ContextMapCsv -Encoding UTF8)' `
    -Label 'Context-map CSV explicit UTF-8 decoding'

try {
    $Utf8NoBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
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
        throw 'Reviewed temporary workbook builder still fails PowerShell parser validation.'
    }

    $TempHash = (Get-FileHash -LiteralPath $TempScript -Algorithm SHA256).Hash

    Write-Host "CanonicalBuilderBlob=PASS — $ActualBuilderBlob"
    Write-Host "ExecutionSourceBlob=PASS — $ExecutionSourceBlob"
    Write-Host 'RepairScope=PASS — exactly one ${CaseIndex}: parser repair'
    Write-Host 'EncodingPatch=PASS — Review CSV explicit UTF8'
    Write-Host 'EncodingPatch=PASS — Context-map CSV explicit UTF8'
    Write-Host 'RepairedParser=PASS'
    Write-Host "TemporaryExecutionSHA256=$TempHash"
    Write-Host "PrivateCheckpoint=PASS — $PrivateHead"
    Write-Host ''
    Write-Host '[execute reviewed temporary workbook builder]'

    $ExecutionStarted = $true

    & $TempScript `
        -PrivateRepo $PrivateRepo `
        -OutputPath $OutputPath `
        -ExpectedPrivateHead $ExpectedPrivateHead

    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "Expected workbook was not created: $OutputPath"
    }

    $WorkbookHash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash
    $ExecutionSucceeded = $true

    Write-Host ''
    Write-Host ('=' * 76)
    Write-Host ' M2 CONTEXT-SUFFICIENCY WORKBOOK REVIEWED RECOVERY COMPLETE'
    Write-Host " Workbook=$OutputPath"
    Write-Host " WorkbookSHA256=$WorkbookHash"
    Write-Host ' ReviewCases=100'
    Write-Host ' HistoricalContextRows=1952'
    Write-Host ' ExpectedReviewHyperlinks=200'
    Write-Host ' ExpectedHistoricalEvidenceHyperlinks=1952'
    Write-Host ' InitialReviewed=0'
    Write-Host ' InitialRemaining=100'
    Write-Host ' GroundTruthAssigned=0'
    Write-Host ' NEXT=complete all 100 Context Sufficiency decisions and upload the saved workbook'
    Write-Host ('=' * 76)
}
catch {
    if ($ExecutionStarted -and -not $ExecutionSucceeded -and (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        Write-Host 'Removing newly generated workbook because execution/validation did not complete successfully...'
        Remove-Item -LiteralPath $OutputPath -Force -ErrorAction SilentlyContinue
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $TempScript) {
        Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
    }
}