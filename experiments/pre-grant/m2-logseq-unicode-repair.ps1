[CmdletBinding()]
param(
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private',
    [string]$CacheRepo = 'C:\DefensiveDrift\source-cache\logseq-restructure'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:GIT_TERMINAL_PROMPT = '0'

if ($PSVersionTable.PSEdition -ne 'Core' -or $PSVersionTable.PSVersion.Major -lt 7) {
    throw ('PowerShell 7+ is required. Current runtime: {0} {1}' -f $PSVersionTable.PSEdition, $PSVersionTable.PSVersion)
}

$GitCommand = Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1
if ($null -eq $GitCommand) {
    throw 'Git executable was not resolved from PATH.'
}
$GitPath = $GitCommand.Source
$Utf8 = [System.Text.UTF8Encoding]::new($false)

function Write-Stage {
    param([string]$Text)
    Write-Host ''
    Write-Host '============================================================================'
    Write-Host (' ' + $Text)
    Write-Host (' Time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'))
    Write-Host '============================================================================'
}

function Invoke-GitUtf8 {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $GitPath
    $StartInfo.WorkingDirectory = $RepoPath
    $StartInfo.UseShellExecute = $false
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.CreateNoWindow = $true
    $StartInfo.StandardOutputEncoding = $Utf8
    $StartInfo.StandardErrorEncoding = $Utf8

    foreach ($Argument in $Arguments) {
        [void]$StartInfo.ArgumentList.Add($Argument)
    }

    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo

    if (-not $Process.Start()) {
        throw ('Unable to start Git in {0}' -f $RepoPath)
    }

    $StdOutTask = $Process.StandardOutput.ReadToEndAsync()
    $StdErrTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    $StdOut = $StdOutTask.GetAwaiter().GetResult()
    $StdErr = $StdErrTask.GetAwaiter().GetResult()
    $ExitCode = $Process.ExitCode
    $Process.Dispose()

    if ($ExitCode -ne 0) {
        throw ('git {0} failed in {1}: {2}' -f ($Arguments -join ' '), $RepoPath, $StdErr.Trim())
    }

    return $StdOut
}

function Get-FlexibleField {
    param(
        [string]$Text,
        [string]$FieldName
    )

    $Escaped = [regex]::Escape($FieldName)
    foreach ($Pattern in @(
        ('(?mi)^\s*(?:[-*]\s*)?\*\*{0}:\*\*\s*(.+?)\s*$' -f $Escaped),
        ('(?mi)^\s*(?:[-*]\s*)?{0}:\s*(.+?)\s*$' -f $Escaped)
    )) {
        $Match = [regex]::Match($Text, $Pattern)
        if ($Match.Success) {
            return $Match.Groups[1].Value.Trim()
        }
    }

    return ''
}

function Get-DiscoveryAssessment {
    param(
        [string]$RelativePath,
        [string]$Text
    )

    $Path = $RelativePath.Replace('\', '/')
    $FileName = [System.IO.Path]::GetFileName($Path)
    $Score = 0
    $Signals = [System.Collections.Generic.List[string]]::new()

    if ($FileName -match '(?i)drift') { $Score += 3; $Signals.Add('filename:drift') }
    if ($Path -match '(?i)(^|/)(drift|drifts|drift-log|drift-logs)(/|$)') { $Score += 2; $Signals.Add('path:drift-container') }
    if ($Path -match '(?i)(^|/)inbox(/|$)') { $Score += 1; $Signals.Add('path:inbox') }
    if ($Text -match '(?mi)(?:\*\*)?Drift ID:(?:\*\*)?') { $Score += 5; $Signals.Add('content:drift-id') }
    if ($Text -match '(?mi)^#\s+.*drift') { $Score += 3; $Signals.Add('content:drift-heading') }
    if ($Text -match '(?i)Drift Log') { $Score += 3; $Signals.Add('content:drift-log') }
    if ($Text -match '(?i)Continuance Drift') { $Score += 2; $Signals.Add('content:continuance-drift') }
    if ($Text -match '(?i)Expected State') { $Score += 1; $Signals.Add('content:expected-state') }
    if ($Text -match '(?i)Actual State') { $Score += 1; $Signals.Add('content:actual-state') }

    return [pscustomobject]@{
        eligible = ($Score -ge 4 -or ($FileName -match '(?i)drift' -and $Text -match '(?i)drift'))
        score = $Score
        signals = ($Signals -join ';')
    }
}

function Get-SourceModel {
    param([string]$Text)

    $Raw = Get-FlexibleField -Text $Text -FieldName 'Model Provenance'
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'Model' }
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'AI Model' }
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'Provider' }

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return [pscustomobject]@{ source_model = 'UNKNOWN'; model_provenance_raw = ''; model_confidence = 'UNKNOWN' }
    }

    $Model = 'OTHER_EXPLICIT'
    if ($Raw -match '(?i)chatgpt|gpt-|openai') { $Model = 'ChatGPT/OpenAI' }
    elseif ($Raw -match '(?i)claude|anthropic') { $Model = 'Claude' }
    elseif ($Raw -match '(?i)gemini|google') { $Model = 'Gemini' }
    elseif ($Raw -match '(?i)perplexity') { $Model = 'Perplexity' }
    elseif ($Raw -match '(?i)copilot') { $Model = 'GitHub Copilot' }
    elseif ($Raw -match '(?i)cline') { $Model = 'Cline' }
    elseif ($Raw -match '(?i)codex') { $Model = 'Codex' }
    elseif ($Raw -match '(?i)ollama|qwen|llama|gemma|mistral|phi') { $Model = 'Open-weight/local model' }

    return [pscustomobject]@{ source_model = $Model; model_provenance_raw = $Raw; model_confidence = 'EXPLICIT_FIELD' }
}

function Get-TemplateFamily {
    param([string]$Text)

    $HasIncidentMetadata = $Text -match '(?m)^##\s+.*Incident Metadata\s*$'
    $HasDetectionProvenance = $Text -match '(?m)^##\s+.*Detection.*Logging Provenance\s*$'
    $HasDriftId = $Text -match '(?mi)(?:\*\*)?Drift ID:(?:\*\*)?'
    $HasDriftHeading = $Text -match '(?mi)^#\s+.*drift'
    $HasDriftLog = $Text -match '(?i)Drift Log'

    if ($HasIncidentMetadata -and $HasDetectionProvenance) { return 'CURRENT_STRUCTURED_VARIANT' }
    if ($HasDriftId -and $HasDriftHeading) { return 'LEGACY_STRUCTURED' }
    if ($HasDriftHeading -or $HasDriftLog) { return 'LEGACY_PARTIAL' }
    return 'UNSTRUCTURED_CANDIDATE'
}

function New-RemoteCandidate {
    param(
        [string]$Repository,
        [string]$Origin,
        [string]$Branch,
        [string]$Commit,
        [string]$RelativePath,
        [string]$BlobSha,
        [long]$Bytes,
        [string]$Text
    )

    $Assessment = Get-DiscoveryAssessment -RelativePath $RelativePath -Text $Text
    if (-not $Assessment.eligible) { return $null }

    $Model = Get-SourceModel -Text $Text
    $TitleMatch = [regex]::Match($Text, '(?m)^#\s+(.+?)\s*$')
    $Title = if ($TitleMatch.Success) { $TitleMatch.Groups[1].Value.Trim() } else { [System.IO.Path]::GetFileNameWithoutExtension($RelativePath) }

    return [pscustomobject]@{
        combined_candidate_id = ''
        prior_candidate_id = ''
        source_state = 'TRACKED_REMOTE_CACHE'
        coverage_origin = 'GITHUB_REMOTE'
        source_repository = $Repository
        source_origin = $Origin
        source_branch = $Branch
        source_commit = $Commit
        repository_head_context = $Commit
        source_relative_path = $RelativePath.Replace('\', '/')
        source_git_blob_sha = $BlobSha
        source_sha256 = ''
        source_bytes = $Bytes
        source_worktree_dirty = $false
        source_model = $Model.source_model
        model_confidence = $Model.model_confidence
        model_provenance_raw = $Model.model_provenance_raw
        template_family = Get-TemplateFamily -Text $Text
        discovery_score = $Assessment.score
        discovery_signals = $Assessment.signals
        title = $Title
        drift_id_raw = Get-FlexibleField -Text $Text -FieldName 'Drift ID'
        severity_raw = Get-FlexibleField -Text $Text -FieldName 'Severity'
        affected_component_raw = Get-FlexibleField -Text $Text -FieldName 'Affected Component'
        recurrence_raw = Get-FlexibleField -Text $Text -FieldName 'Recurrence Classification'
        review_status = 'UNREVIEWED'
        normalization_status = 'NOT_STARTED'
        proposed_case_id = ''
        notes = ''
    }
}

function Write-Utf8OneFinalNewline {
    param(
        [string]$Path,
        [string]$Text
    )

    $Normalized = $Text.TrimEnd("`r", "`n") + "`n"
    [System.IO.File]::WriteAllText($Path, $Normalized, $Utf8)
}

Write-Stage 'DEFENSIVE DRIFT - M2 LOGSEQ UNICODE COVERAGE REPAIR'
Write-Host ('Runtime: PowerShell {0} / {1}' -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)
Write-Host ('Git: {0}' -f $GitPath)
Write-Host 'Scope: repair only logseq-restructure remote coverage'
Write-Host 'Original local source repositories: NOT TOUCHED'

if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) {
    throw ('Private research repository not found: {0}' -f $PrivateRepo)
}
if (-not (Test-Path -LiteralPath (Join-Path $CacheRepo '.git') -PathType Container)) {
    throw ('logseq-restructure cache repository not found: {0}' -f $CacheRepo)
}

$OutputRoot = Join-Path $PrivateRepo 'source-index\comprehensive'
$CombinedJson = Join-Path $OutputRoot 'combined-drift-evidence-candidates.json'
$CombinedCsv = Join-Path $OutputRoot 'combined-drift-evidence-candidates.csv'
$CoverageCsv = Join-Path $OutputRoot 'repository-coverage.csv'
$SummaryMd = Join-Path $OutputRoot 'coverage-summary.md'

foreach ($Required in @($CombinedJson, $CombinedCsv, $CoverageCsv, $SummaryMd)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw ('Required partial M2 artifact missing: {0}' -f $Required)
    }
}

Write-Host ''
Write-Host '[1/5] Validate preserved partial checkpoint...'
$PrivateStatus = Invoke-GitUtf8 -RepoPath $PrivateRepo -Arguments @('status', '--porcelain=v1', '--untracked-files=all')
if (-not [string]::IsNullOrWhiteSpace($PrivateStatus)) {
    Write-Host $PrivateStatus
    throw 'Private research repository is not clean. Repair aborted.'
}

$PrivateHead = (Invoke-GitUtf8 -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')).Trim()
if ($PrivateHead -ne 'e87f01dd9ee100ad69ffb89caa7d5dc7223ef02a') {
    throw ('Unexpected private checkpoint. Expected e87f01dd9ee100ad69ffb89caa7d5dc7223ef02a, found {0}' -f $PrivateHead)
}

$Combined = @((Get-Content -LiteralPath $CombinedJson -Raw | ConvertFrom-Json))
$Coverage = @(Import-Csv -LiteralPath $CoverageCsv)
if ($Combined.Count -ne 1912) {
    throw ('Unexpected combined candidate count. Expected 1912, found {0}' -f $Combined.Count)
}

$FailedRows = @($Coverage | Where-Object { $_.disposition -eq 'REMOTE_SCAN_FAILED' })
if ($FailedRows.Count -ne 1 -or $FailedRows[0].repository -ne 'logseq-restructure') {
    throw 'Expected exactly one failed repository row for logseq-restructure.'
}

Write-Host ('  Private checkpoint: {0}' -f $PrivateHead)
Write-Host ('  Preserved candidates: {0}' -f $Combined.Count)
Write-Host '  Sole remaining failure: logseq-restructure'

Write-Host ''
Write-Host '[2/5] Enumerate logseq-restructure tree with explicit UTF-8 decoding...'
$Commit = (Invoke-GitUtf8 -RepoPath $CacheRepo -Arguments @('rev-parse', 'HEAD')).Trim()
$RawTree = Invoke-GitUtf8 -RepoPath $CacheRepo -Arguments @('ls-tree', '-r', '-z', 'HEAD')
$TreeRecords = @($RawTree.Split([char]0, [System.StringSplitOptions]::RemoveEmptyEntries))

$MarkdownEntries = [System.Collections.Generic.List[object]]::new()
$UnicodeMarkdownCount = 0
foreach ($Record in $TreeRecords) {
    $TabIndex = $Record.IndexOf("`t")
    if ($TabIndex -lt 0) { throw ('Malformed ls-tree record: {0}' -f $Record) }

    $Metadata = $Record.Substring(0, $TabIndex)
    $RelativePath = $Record.Substring($TabIndex + 1)
    $Parts = @($Metadata -split '\s+')
    if ($Parts.Count -lt 3) { throw ('Malformed ls-tree metadata: {0}' -f $Metadata) }
    if ($Parts[1] -ne 'blob') { continue }
    if (-not $RelativePath.EndsWith('.md', [System.StringComparison]::OrdinalIgnoreCase)) { continue }

    if ($RelativePath.ToCharArray() | Where-Object { [int]$_ -gt 127 } | Select-Object -First 1) {
        $UnicodeMarkdownCount++
    }

    $MarkdownEntries.Add([pscustomobject]@{
        path = $RelativePath
        blob_sha = $Parts[2]
    })
}

if ($MarkdownEntries.Count -ne 1415) {
    throw ('Unicode-safe enumeration count changed. Expected 1415 Markdown files, found {0}.' -f $MarkdownEntries.Count)
}
if ($UnicodeMarkdownCount -lt 1) {
    throw 'Unicode-path preflight failed: no non-ASCII Markdown path was decoded.'
}

$TargetSentinel = @(
    $MarkdownEntries |
    Where-Object { $_.path -like '*SPC Homelab Personal Setup Script*Concept*Project Summary.md' }
)
if ($TargetSentinel.Count -ne 1) {
    throw ('Expected one Unicode-path sentinel matching the previously failed SPC Homelab document; found {0}.' -f $TargetSentinel.Count)
}
Write-Host ('  Tree records: {0}' -f $TreeRecords.Count)
Write-Host ('  Markdown files: {0}' -f $MarkdownEntries.Count)
Write-Host ('  Unicode Markdown paths: {0}' -f $UnicodeMarkdownCount)
Write-Host ('  Unicode sentinel: PASS — {0}' -f $TargetSentinel[0].path)

Write-Host ''
Write-Host '[3/5] Rescan only logseq-restructure blobs by SHA...'
$ExistingLogseq = @(
    $Combined |
    Where-Object { $_.coverage_origin -eq 'GITHUB_REMOTE' -and $_.source_repository -eq 'logseq-restructure' }
)
$BaseCombined = @(
    $Combined |
    Where-Object { -not ($_.coverage_origin -eq 'GITHUB_REMOTE' -and $_.source_repository -eq 'logseq-restructure') }
)

$LogseqCandidates = [System.Collections.Generic.List[object]]::new()
$MaxBytes = 5MB
$Oversized = 0
$CloneUrl = 'https://github.com/MikeHacksAI/logseq-restructure.git'
foreach ($Entry in $MarkdownEntries) {
    $SizeText = (Invoke-GitUtf8 -RepoPath $CacheRepo -Arguments @('cat-file', '-s', $Entry.blob_sha)).Trim()
    $Bytes = [long]$SizeText
    if ($Bytes -gt $MaxBytes) { $Oversized++; continue }

    $Text = Invoke-GitUtf8 -RepoPath $CacheRepo -Arguments @('cat-file', 'blob', $Entry.blob_sha)
    $Candidate = New-RemoteCandidate `
        -Repository 'logseq-restructure' `
        -Origin $CloneUrl `
        -Branch 'REMOTE_DEFAULT' `
        -Commit $Commit `
        -RelativePath $Entry.path `
        -BlobSha $Entry.blob_sha `
        -Bytes $Bytes `
        -Text $Text

    if ($null -ne $Candidate) { $LogseqCandidates.Add($Candidate) }
}

$FinalCombined = [System.Collections.Generic.List[object]]::new()
foreach ($Item in $BaseCombined) { $FinalCombined.Add($Item) }
foreach ($Item in $LogseqCandidates) { $FinalCombined.Add($Item) }
for ($Index = 0; $Index -lt $FinalCombined.Count; $Index++) {
    $FinalCombined[$Index].combined_candidate_id = ('M2C-{0:D6}' -f ($Index + 1))
}

Write-Host ('  Previously preserved partial logseq candidates removed: {0}' -f $ExistingLogseq.Count)
Write-Host ('  Unicode-safe logseq candidates: {0}' -f $LogseqCandidates.Count)
Write-Host ('  Oversized Markdown excluded: {0}' -f $Oversized)
Write-Host ('  Rebuilt combined candidates: {0}' -f $FinalCombined.Count)

Write-Host ''
Write-Host '[4/5] Rebuild coverage and final private artifacts...'
foreach ($Row in $Coverage) {
    if ($Row.repository -eq 'logseq-restructure') {
        $Row.disposition = 'REMOTE_SOURCE_AUDITED'
        $Row.remote_markdown_count = [string]$MarkdownEntries.Count
    }
}

$RemainingFailures = @($Coverage | Where-Object { $_.disposition -eq 'REMOTE_SCAN_FAILED' })
if ($RemainingFailures.Count -ne 0) {
    throw ('Coverage still contains {0} REMOTE_SCAN_FAILED row(s).' -f $RemainingFailures.Count)
}

$RemoteMarkdownTotal = 0
foreach ($Row in $Coverage) {
    if (-not [string]::IsNullOrWhiteSpace($Row.remote_markdown_count)) {
        $RemoteMarkdownTotal += [int]$Row.remote_markdown_count
    }
}
$RemoteCandidateTotal = @($FinalCombined | Where-Object { $_.coverage_origin -eq 'GITHUB_REMOTE' }).Count
$EmptyRepositoryTotal = @($Coverage | Where-Object { $_.disposition -eq 'EMPTY_REPOSITORY_NO_COMMIT_TREE' }).Count

$CombinedCsvText = ((@($FinalCombined) | ConvertTo-Csv -NoTypeInformation) -join "`n")
$CombinedJsonText = (@($FinalCombined) | ConvertTo-Json -Depth 7
$CoverageCsvText = ((@($Coverage) | ConvertTo-Csv -NoTypeInformation) -join "`n")
$SummaryText = @"
# Defensive Drift M2 Comprehensive Corpus Coverage

Finalized: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')

## Counts

- GitHub repository snapshot: **65**
- Local/checkpoint candidate records before remote repair: **1901**
- GitHub-only repositories audited through remote cache: **40**
- Empty repositories with no commit tree: **$EmptyRepositoryTotal**
- GitHub-only tracked Markdown scanned after Unicode-safe repair: **$RemoteMarkdownTotal**
- GitHub-remote drift candidates: **$RemoteCandidateTotal**
- Combined candidate records: **$($FinalCombined.Count)**
- Remaining remote repository scan failures: **0**

## Final coverage state

- All source evidence remained read-only.
- The successful local/checkpoint corpus work was preserved.
- `logseq-restructure` was repaired using explicit UTF-8 decoding of NUL-delimited `git ls-tree` output.
- Blob SHA values were taken directly from the Git tree, so Unicode paths were not reconstructed into `HEAD:<path>` revision expressions.
- Empty repositories remain classified as covered repositories with no commit tree.
- Discovery scoring remains a high-recall review-pool heuristic; human adjudication creates benchmark ground truth.
- Corpus completeness is now eligible for milestone-gate review; this file does not itself declare the benchmark frozen.
"@

Write-Utf8OneFinalNewline -Path $CombinedCsv -Text $CombinedCsvText
Write-Utf8OneFinalNewline -Path $CombinedJson -Text $CombinedJsonText
Write-Utf8OneFinalNewline -Path $CoverageCsv -Text $CoverageCsvText
Write-Utf8OneFinalNewline -Path $SummaryMd -Text $SummaryText

$CombinedHash = (Get-FileHash -LiteralPath $CombinedCsv -Algorithm SHA256).Hash.ToLowerInvariant()

& git -C $PrivateRepo add -- `
    'source-index/comprehensive/combined-drift-evidence-candidates.csv' `
    'source-index/comprehensive/combined-drift-evidence-candidates.json' `
    'source-index/comprehensive/repository-coverage.csv' `
    'source-index/comprehensive/coverage-summary.md'
if ($LASTEXITCODE -ne 0) { throw 'Staging final corpus artifacts failed.' }

& git -C $PrivateRepo diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Final corpus artifact whitespace validation failed.' }

$Staged = (Invoke-GitUtf8 -RepoPath $PrivateRepo -Arguments @('diff', '--cached', '--name-only')).Trim()
if ([string]::IsNullOrWhiteSpace($Staged)) {
    throw 'No final M2 corpus changes were staged.'
}

& git -C $PrivateRepo commit -m 'Complete M2 corpus coverage after Unicode repair'
if ($LASTEXITCODE -ne 0) { throw 'Private corpus repair commit failed.' }
& git -C $PrivateRepo push origin main
if ($LASTEXITCODE -ne 0) { throw 'Private corpus repair push failed.' }
$FinalPrivateCommit = (Invoke-GitUtf8 -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')).Trim()

Write-Host ''
Write-Host '[5/5] Final verification...'
$FinalStatus = Invoke-GitUtf8 -RepoPath $PrivateRepo -Arguments @('status', '--porcelain=v1', '--untracked-files=all')
if (-not [string]::IsNullOrWhiteSpace($FinalStatus)) {
    Write-Host $FinalStatus
    throw 'Private research repository is not clean after final repair commit.'
}

Write-Stage 'M2 LOGSEQ UNICODE COVERAGE REPAIR FINISHED'
Write-Host ('LogseqMarkdownScanned={0}' -f $MarkdownEntries.Count)
Write-Host ('LogseqCandidates={0}' -f $LogseqCandidates.Count)
Write-Host ('RemoteMarkdownTotal={0}' -f $RemoteMarkdownTotal)
Write-Host ('RemoteCandidatesTotal={0}' -f $RemoteCandidateTotal)
Write-Host ('CombinedCandidates={0}' -f $FinalCombined.Count)
Write-Host ('RemainingRemoteFailures={0}' -f $RemainingFailures.Count)
Write-Host ('CombinedInventorySHA256={0}' -f $CombinedHash)
Write-Host ('PrivateCommit={0}' -f $FinalPrivateCommit)
Write-Host 'OriginalSourceRepositoriesModified=0'
Write-Host 'FINAL STATUS: SUCCESS — M2 corpus coverage repaired; proceed to corpus-completeness gate review.'
