[CmdletBinding()]
param(
    [string]$Repo = 'C:\GitHub\openai-defensive-drift'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7) {
    throw ('PowerShell 7+ is required. Current runtime: {0} {1}' -f $PSVersionTable.PSEdition, $PSVersionTable.PSVersion)
}

$RelativeBrokenScript = 'experiments/pre-grant/m2-logseq-unicode-repair.ps1'
$BrokenBlob = '0c1a604a6419d415d614f20d6ce9fa738658084d'
$BrokenLine = '$CombinedJsonText = (@($FinalCombined) | ConvertTo-Json -Depth 7'
$FixedLine = '$CombinedJsonText = (@($FinalCombined) | ConvertTo-Json -Depth 7)'

if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git') -PathType Container)) {
    throw ('Public repository not found: {0}' -f $Repo)
}

Set-Location $Repo

$ActualBlob = (& git rev-parse ('HEAD:{0}' -f $RelativeBrokenScript)).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to resolve the known Unicode-repair script blob.'
}
if ($ActualBlob -ne $BrokenBlob) {
    throw ('Known broken script changed. Expected blob {0}; found {1}. Refusing implicit patch.' -f $BrokenBlob, $ActualBlob)
}

$BrokenPath = Join-Path $Repo $RelativeBrokenScript
$Source = [System.IO.File]::ReadAllText($BrokenPath)
$Occurrences = ([regex]::Matches($Source, [regex]::Escape($BrokenLine))).Count
if ($Occurrences -ne 1) {
    throw ('Expected exactly one known missing-parenthesis line; found {0}.' -f $Occurrences)
}

$FixedSource = $Source.Replace($BrokenLine, $FixedLine)
if ($FixedSource -eq $Source) {
    throw 'Known parser defect was not changed.'
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'defensive-drift-m2'
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
$TempScript = Join-Path $TempRoot 'm2-logseq-unicode-repair-fixed.ps1'
[System.IO.File]::WriteAllText($TempScript, $FixedSource, [System.Text.UTF8Encoding]::new($false))

$Tokens = $null
$ParseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $TempScript,
    [ref]$Tokens,
    [ref]$ParseErrors
) | Out-Null

if ($ParseErrors.Count -gt 0) {
    $ParseErrors | Format-List -Force
    throw 'Repaired temporary script still fails the PowerShell parser. Nothing executed.'
}

$Analyzer = Get-Command Invoke-ScriptAnalyzer -ErrorAction SilentlyContinue
if ($null -eq $Analyzer) {
    throw 'PSScriptAnalyzer is unavailable. Nothing executed.'
}

$Diagnostics = @(Invoke-ScriptAnalyzer -Path $TempScript -Severity Error)
if ($Diagnostics.Count -gt 0) {
    $Diagnostics | Format-Table -AutoSize
    throw 'Repaired temporary script fails PSScriptAnalyzer. Nothing executed.'
}

Write-Host 'Known parser defect patched in temporary copy only.'
Write-Host ('Broken source blob: {0}' -f $BrokenBlob)
Write-Host ('Temporary repaired script: {0}' -f $TempScript)
Write-Host 'Parser: PASS'
Write-Host 'PSScriptAnalyzer: PASS'
Write-Host ''
Write-Host 'Starting focused logseq-restructure Unicode repair...'
Write-Host ''

& $TempScript
$ExitCode = $LASTEXITCODE
if ($null -ne $ExitCode -and $ExitCode -ne 0) {
    throw ('Focused Unicode repair exited with code {0}.' -f $ExitCode)
}
