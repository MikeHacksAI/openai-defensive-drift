[CmdletBinding()]
param(
    [string]$GitRoot = 'C:\GitHub',
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:GIT_TERMINAL_PROMPT = '0'

function Write-Stage {
    param([string]$Text)
    Write-Host ''
    Write-Host '============================================================================'
    Write-Host (' ' + $Text)
    Write-Host (' Time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'))
    Write-Host '============================================================================'
}

function Assert-ExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw ('{0} failed with exit code {1}' -f $Step, $LASTEXITCODE)
    }
}

function Get-GitValue {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $Value = (& git -C $RepoPath @Arguments 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return ''
    }

    return (($Value | Out-String).Trim())
}

function Get-FlexibleField {
    param(
        [string]$Text,
        [string]$FieldName
    )

    $Escaped = [regex]::Escape($FieldName)
    $Patterns = @(
        ('(?mi)^\s*(?:[-*]\s*)?\*\*{0}:\*\*\s*(.+?)\s*$' -f $Escaped),
        ('(?mi)^\s*(?:[-*]\s*)?{0}:\s*(.+?)\s*$' -f $Escaped)
    )

    foreach ($Pattern in $Patterns) {
        $Match = [regex]::Match($Text, $Pattern)
        if ($Match.Success) {
            return $Match.Groups[1].Value.Trim()
        }
    }

    return ''
}

function Get-SourceModel {
    param(
        [string]$RepositoryName,
        [string]$RelativePath,
        [string]$Text
    )

    $NormalizedPath = $RelativePath.Replace('\', '/')

    # Operator-established corpus rule: raw/confirmed-incidents is the curated ChatGPT stream.
    if (
        $RepositoryName -eq 'mikehacksai-drift-records' -and
        $NormalizedPath -match '^raw/confirmed-incidents/'
    ) {
        return [pscustomobject]@{
            source_model = 'ChatGPT'
            model_provenance_raw = 'Path-classified by operator-established corpus rule: raw/confirmed-incidents is ChatGPT-only.'
            model_confidence = 'OPERATOR_CONFIRMED'
        }
    }

    $Raw = Get-FlexibleField -Text $Text -FieldName 'Model Provenance'
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        $Raw = Get-FlexibleField -Text $Text -FieldName 'Model'
    }
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        $Raw = Get-FlexibleField -Text $Text -FieldName 'AI Model'
    }
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        $Raw = Get-FlexibleField -Text $Text -FieldName 'Provider'
    }

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return [pscustomobject]@{
            source_model = 'UNKNOWN'
            model_provenance_raw = ''
            model_confidence = 'UNKNOWN'
        }
    }

    $Model = 'OTHER_EXPLICIT'
    if ($Raw -match '(?i)chatgpt|gpt-') {
        $Model = 'ChatGPT/OpenAI'
    }
    elseif ($Raw -match '(?i)claude') {
        $Model = 'Claude'
    }
    elseif ($Raw -match '(?i)gemini') {
        $Model = 'Gemini'
    }
    elseif ($Raw -match '(?i)perplexity') {
        $Model = 'Perplexity'
    }
    elseif ($Raw -match '(?i)copilot') {
        $Model = 'GitHub Copilot'
    }
    elseif ($Raw -match '(?i)cline') {
        $Model = 'Cline'
    }
    elseif ($Raw -match '(?i)codex') {
        $Model = 'Codex'
    }
    elseif ($Raw -match '(?i)ollama|qwen|llama|gemma|mistral|phi') {
        $Model = 'Open-weight/local model'
    }

    return [pscustomobject]@{
        source_model = $Model
        model_provenance_raw = $Raw
        model_confidence = 'EXPLICIT_FIELD'
    }
}

function Get-TemplateFamily {
    param(
        [string]$RepositoryName,
        [string]$RelativePath,
        [string]$Text
    )

    $NormalizedPath = $RelativePath.Replace('\', '/')
    $HasIncidentMetadata = $Text -match '(?m)^##\s+.*Incident Metadata\s*$'
    $HasDetectionProvenance = $Text -match '(?m)^##\s+.*Detection.*Logging Provenance\s*$'
    $HasDriftId = $Text -match '(?mi)(?:\*\*)?Drift ID:(?:\*\*)?'
    $HasDriftHeading = $Text -match '(?mi)^#\s+.*drift'
    $HasDriftLog = $Text -match '(?i)Drift Log'

    if (
        $RepositoryName -eq 'mikehacksai-drift-records' -and
        $NormalizedPath -match '^raw/confirmed-incidents/' -and
        $HasIncidentMetadata -and
        $HasDetectionProvenance
    ) {
        return 'CHATGPT_CURRENT_CANONICAL'
    }

    if ($HasIncidentMetadata -and $HasDetectionProvenance) {
        return 'CURRENT_STRUCTURED_VARIANT'
    }

    if ($HasDriftId -and $HasDriftHeading) {
        return 'LEGACY_STRUCTURED'
    }

    if ($HasDriftHeading -or $HasDriftLog) {
        return 'LEGACY_PARTIAL'
    }

    return 'UNSTRUCTURED_CANDIDATE'
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

    if ($FileName -match '(?i)drift') {
        $Score += 3
        $Signals.Add('filename:drift')
    }

    if ($Path -match '(?i)(^|/)(drift|drifts|drift-log|drift-logs)(/|$)') {
        $Score += 2
        $Signals.Add('path:drift-container')
    }

    if ($Path -match '(?i)(^|/)inbox(/|$)') {
        $Score += 1
        $Signals.Add('path:inbox')
    }

    if ($Text -match '(?mi)(?:\*\*)?Drift ID:(?:\*\*)?') {
        $Score += 5
        $Signals.Add('content:drift-id')
    }

    if ($Text -match '(?mi)^#\s+.*drift') {
        $Score += 3
        $Signals.Add('content:drift-heading')
    }

    if ($Text -match '(?i)Drift Log') {
        $Score += 3
        $Signals.Add('content:drift-log')
    }

    if ($Text -match '(?i)Continuance Drift') {
        $Score += 2
        $Signals.Add('content:continuance-drift')
    }

    if ($Text -match '(?i)Expected State') {
        $Score += 1
        $Signals.Add('content:expected-state')
    }

    if ($Text -match '(?i)Actual State') {
        $Score += 1
        $Signals.Add('content:actual-state')
    }

    $Eligible = $false
    if ($Score -ge 4) {
        $Eligible = $true
    }
    elseif (
        $FileName -match '(?i)drift' -and
        $Text -match '(?i)drift'
    ) {
        $Eligible = $true
    }

    return [pscustomobject]@{
        eligible = $Eligible
        score = $Score
        signals = ($Signals -join ';')
    }
}

function Get-TrackedMarkdownFiles {
    param([string]$RepoPath)

    $Files = @(& git -C $RepoPath ls-files -- '*.md')
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    return @($Files | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

Write-Stage 'DEFENSIVE DRIFT - M2 CROSS-MODEL EVIDENCE DISCOVERY'
Write-Host 'Mode: READ-ONLY against source repositories'
Write-Host 'Writes: openai-defensive-drift-private only'

if (-not (Test-Path $GitRoot)) {
    throw ('Git root not found: {0}' -f $GitRoot)
}

if (-not (Test-Path (Join-Path $PrivateRepo '.git'))) {
    throw ('Private Defensive Drift clone not found: {0}' -f $PrivateRepo)
}

Write-Host ''
Write-Host '[1/6] Verify private workspace...'
$PrivateDirty = @(& git -C $PrivateRepo status --porcelain)
Assert-ExitCode 'Read private workspace status'
if ($PrivateDirty.Count -gt 0) {
    Write-Host 'UNCOMMITTED PRIVATE WORKSPACE CHANGES:'
    $PrivateDirty | ForEach-Object { Write-Host ('  ' + $_) }
    throw 'Refusing to overwrite an unclean private research workspace.'
}

& git -C $PrivateRepo pull --ff-only origin main
Assert-ExitCode 'Sync private workspace'

Write-Host ''
Write-Host '[2/6] Discover local Git repositories...'
$Repos = @(
    Get-ChildItem -Path $GitRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName '.git') } |
    Sort-Object Name
)

if ($Repos.Count -eq 0) {
    throw ('No Git repositories found under {0}' -f $GitRoot)
}

Write-Host ('  Repositories found: {0}' -f $Repos.Count)

$ExcludedRepositories = @(
    'openai-defensive-drift',
    'openai-defensive-drift-private'
)

$SourceSnapshots = [System.Collections.Generic.List[object]]::new()
$Candidates = [System.Collections.Generic.List[object]]::new()
$CandidateNumber = 0
$ReposScanned = 0
$MarkdownFilesScanned = 0

Write-Host ''
Write-Host '[3/6] Scan tracked Markdown for drift evidence...'

foreach ($Repo in $Repos) {
    if ($ExcludedRepositories -contains $Repo.Name) {
        continue
    }

    $ReposScanned++
    $Origin = Get-GitValue -RepoPath $Repo.FullName -Arguments @('remote', 'get-url', 'origin')
    $Head = Get-GitValue -RepoPath $Repo.FullName -Arguments @('rev-parse', 'HEAD')
    $Branch = Get-GitValue -RepoPath $Repo.FullName -Arguments @('branch', '--show-current')
    $StatusBefore = ((& git -C $Repo.FullName status --porcelain) -join "`n")
    Assert-ExitCode ('Read source status for ' + $Repo.Name)

    $SourceSnapshots.Add([pscustomobject]@{
        repository = $Repo.Name
        path = $Repo.FullName
        origin = $Origin
        branch = $Branch
        head = $Head
        status_before = $StatusBefore
    })

    $TrackedMarkdown = @(Get-TrackedMarkdownFiles -RepoPath $Repo.FullName)
    Write-Host ('  [{0}/{1}] {2}: {3} tracked Markdown files' -f $ReposScanned, ($Repos.Count - $ExcludedRepositories.Count), $Repo.Name, $TrackedMarkdown.Count)

    foreach ($RelativePath in $TrackedMarkdown) {
        $MarkdownFilesScanned++
        $FullPath = Join-Path $Repo.FullName ($RelativePath -replace '/', '\')
        if (-not (Test-Path $FullPath -PathType Leaf)) {
            continue
        }

        try {
            $Text = [System.IO.File]::ReadAllText($FullPath)
        }
        catch {
            continue
        }

        $Assessment = Get-DiscoveryAssessment -RelativePath $RelativePath -Text $Text
        if (-not $Assessment.eligible) {
            continue
        }

        $CandidateNumber++
        $NormalizedPath = $RelativePath.Replace('\', '/')
        $BlobSha = Get-GitValue -RepoPath $Repo.FullName -Arguments @('rev-parse', ('HEAD:{0}' -f $NormalizedPath))
        $Sha256 = (Get-FileHash -Path $FullPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $Model = Get-SourceModel -RepositoryName $Repo.Name -RelativePath $NormalizedPath -Text $Text
        $TemplateFamily = Get-TemplateFamily -RepositoryName $Repo.Name -RelativePath $NormalizedPath -Text $Text

        $TitleMatch = [regex]::Match($Text, '(?m)^#\s+(.+?)\s*$')
        $Title = if ($TitleMatch.Success) { $TitleMatch.Groups[1].Value.Trim() } else { [System.IO.Path]::GetFileNameWithoutExtension($NormalizedPath) }

        $Candidates.Add([pscustomobject]@{
            candidate_id = ('DISC-{0:D5}' -f $CandidateNumber)
            source_repository = $Repo.Name
            source_origin = $Origin
            source_branch = $Branch
            source_commit = $Head
            source_relative_path = $NormalizedPath
            source_git_blob_sha = $BlobSha
            source_sha256 = $Sha256
            source_bytes = (Get-Item $FullPath).Length
            source_worktree_dirty = -not [string]::IsNullOrWhiteSpace($StatusBefore)
            source_model = $Model.source_model
            model_confidence = $Model.model_confidence
            model_provenance_raw = $Model.model_provenance_raw
            template_family = $TemplateFamily
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
        })
    }
}

Write-Host ('  Repositories scanned: {0}' -f $ReposScanned)
Write-Host ('  Markdown files scanned: {0}' -f $MarkdownFilesScanned)
Write-Host ('  Drift candidates discovered: {0}' -f $Candidates.Count)

Write-Host ''
Write-Host '[4/6] Verify every source repository remained unchanged...'
foreach ($Snapshot in $SourceSnapshots) {
    $HeadAfter = Get-GitValue -RepoPath $Snapshot.path -Arguments @('rev-parse', 'HEAD')
    $StatusAfter = ((& git -C $Snapshot.path status --porcelain) -join "`n")
    Assert-ExitCode ('Re-read source status for ' + $Snapshot.repository)

    if ($HeadAfter -ne $Snapshot.head) {
        throw ('Source HEAD changed during discovery: {0}' -f $Snapshot.repository)
    }

    if ($StatusAfter -ne $Snapshot.status_before) {
        throw ('Source worktree changed during discovery: {0}' -f $Snapshot.repository)
    }
}
Write-Host '  SOURCE INTEGRITY CHECK: PASS'

Write-Host ''
Write-Host '[5/6] Write cross-model inventory to private workspace...'
$OutputRoot = Join-Path $PrivateRepo 'source-index\cross-model'
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$CsvPath = Join-Path $OutputRoot 'drift-evidence-candidates.csv'
$JsonPath = Join-Path $OutputRoot 'drift-evidence-candidates.json'
$SummaryPath = Join-Path $OutputRoot 'discovery-summary.md'
$SnapshotPath = Join-Path $OutputRoot 'source-repository-snapshots.json'

$Candidates | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding utf8
$Candidates | ConvertTo-Json -Depth 6 | Set-Content -Path $JsonPath -Encoding utf8
$SourceSnapshots | ConvertTo-Json -Depth 6 | Set-Content -Path $SnapshotPath -Encoding utf8

$ByRepo = @($Candidates | Group-Object source_repository | Sort-Object Count -Descending)
$ByModel = @($Candidates | Group-Object source_model | Sort-Object Count -Descending)
$ByTemplate = @($Candidates | Group-Object template_family | Sort-Object Count -Descending)

$Lines = [System.Collections.Generic.List[string]]::new()
$Lines.Add('# Defensive Drift - Cross-Model Evidence Discovery')
$Lines.Add('')
$Lines.Add(('Generated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')))
$Lines.Add('')
$Lines.Add('## Discovery totals')
$Lines.Add('')
$Lines.Add(('- Local Git repositories scanned: **{0}**' -f $ReposScanned))
$Lines.Add(('- Tracked Markdown files scanned: **{0}**' -f $MarkdownFilesScanned))
$Lines.Add(('- Drift evidence candidates discovered: **{0}**' -f $Candidates.Count))
$Lines.Add('')
$Lines.Add('## By source repository')
$Lines.Add('')
$Lines.Add('| Repository | Candidates |')
$Lines.Add('|---|---:|')
foreach ($Group in $ByRepo) {
    $Lines.Add(('| {0} | {1} |' -f $Group.Name.Replace('|', '/'), $Group.Count))
}
$Lines.Add('')
$Lines.Add('## By source AI/model')
$Lines.Add('')
$Lines.Add('| Model provenance | Candidates |')
$Lines.Add('|---|---:|')
foreach ($Group in $ByModel) {
    $Lines.Add(('| {0} | {1} |' -f $Group.Name.Replace('|', '/'), $Group.Count))
}
$Lines.Add('')
$Lines.Add('## By template family')
$Lines.Add('')
$Lines.Add('| Template family | Candidates |')
$Lines.Add('|---|---:|')
foreach ($Group in $ByTemplate) {
    $Lines.Add(('| {0} | {1} |' -f $Group.Name.Replace('|', '/'), $Group.Count))
}
$Lines.Add('')
$Lines.Add('## Corpus rules')
$Lines.Add('')
$Lines.Add('- `mikehacksai-drift-records/raw/confirmed-incidents/` is the curated ChatGPT stream, not the entire evidence universe.')
$Lines.Add('- Historical records from other AI models and older storage conventions remain valid candidates.')
$Lines.Add('- Template mismatch does not invalidate evidence.')
$Lines.Add('- Unknown model provenance remains `UNKNOWN`; it is never guessed.')
$Lines.Add('- No source record was moved, renamed, rewritten, deleted, normalized in place, or committed during discovery.')
$Lines.Add('- All normalization and adjudication occurs as derived material in the private Defensive Drift workspace.')

[System.IO.File]::WriteAllLines($SummaryPath, $Lines, [System.Text.UTF8Encoding]::new($false))

$InventoryHash = (Get-FileHash -Path $CsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host ('  Inventory SHA256: {0}' -f $InventoryHash)

Write-Host ''
Write-Host '[6/6] Commit private discovery artifacts...'
& git -C $PrivateRepo add 'source-index/cross-model'
Assert-ExitCode 'Stage cross-model discovery artifacts'

& git -C $PrivateRepo diff --cached --check
Assert-ExitCode 'Validate staged cross-model discovery artifacts'

$Staged = @(& git -C $PrivateRepo diff --cached --name-only)
if ($Staged.Count -eq 0) {
    throw 'No cross-model discovery artifacts were staged.'
}

& git -C $PrivateRepo commit -m 'Inventory cross-model drift evidence corpus'
Assert-ExitCode 'Commit cross-model discovery artifacts'

& git -C $PrivateRepo push origin main
Assert-ExitCode 'Push cross-model discovery artifacts'

$PrivateHead = Get-GitValue -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')

Write-Stage 'M2 CROSS-MODEL DISCOVERY FINISHED: SUCCESS'
Write-Host ('RepositoriesScanned={0}' -f $ReposScanned)
Write-Host ('MarkdownFilesScanned={0}' -f $MarkdownFilesScanned)
Write-Host ('CandidatesDiscovered={0}' -f $Candidates.Count)
Write-Host ('InventorySHA256={0}' -f $InventoryHash)
Write-Host ('PrivateCommit={0}' -f $PrivateHead)
Write-Host 'SourceRepositoriesModified=0'
