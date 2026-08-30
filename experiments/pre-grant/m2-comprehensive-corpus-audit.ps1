[CmdletBinding()]
param(
    [string]$GitRoot = 'C:\GitHub',
    [string]$PrivateRepo = 'C:\GitHub\openai-defensive-drift-private',
    [string]$CacheRoot = 'C:\DefensiveDrift\source-cache'
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

function Write-Stage {
    param([string]$Text)
    Write-Host ''
    Write-Host '============================================================================'
    Write-Host (' ' + $Text)
    Write-Host (' Time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'))
    Write-Host '============================================================================'
}

function Assert-GitExit {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw ('{0} failed with exit code {1}' -f $Step, $LASTEXITCODE)
    }
}

function Invoke-GitText {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $Output = @(& git -C $RepoPath @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw ('git {0} failed in {1}: {2}' -f ($Arguments -join ' '), $RepoPath, (($Output | Out-String).Trim()))
    }

    return (($Output | Out-String).TrimEnd())
}

function Invoke-GitNullList {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $Output = @(& git -C $RepoPath @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw ('git {0} failed in {1}' -f ($Arguments -join ' '), $RepoPath)
    }

    if ($Output.Count -eq 0) {
        return @()
    }

    $Raw = ($Output -join "`n")
    if ([string]::IsNullOrEmpty($Raw)) {
        return @()
    }

    return @(
        $Raw.Split(
            [char[]]@([char]0),
            [System.StringSplitOptions]::RemoveEmptyEntries
        )
    )
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

    if (
        $RepositoryName -eq 'mikehacksai-drift-records' -and
        $NormalizedPath -match '^raw/confirmed-incidents/'
    ) {
        return [pscustomobject]@{
            source_model = 'ChatGPT'
            model_provenance_raw = 'Operator-confirmed corpus rule: raw/confirmed-incidents is ChatGPT-only.'
            model_confidence = 'OPERATOR_CONFIRMED'
        }
    }

    $Raw = Get-FlexibleField -Text $Text -FieldName 'Model Provenance'
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'Model' }
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'AI Model' }
    if ([string]::IsNullOrWhiteSpace($Raw)) { $Raw = Get-FlexibleField -Text $Text -FieldName 'Provider' }

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return [pscustomobject]@{
            source_model = 'UNKNOWN'
            model_provenance_raw = ''
            model_confidence = 'UNKNOWN'
        }
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

    if ($HasIncidentMetadata -and $HasDetectionProvenance) { return 'CURRENT_STRUCTURED_VARIANT' }
    if ($HasDriftId -and $HasDriftHeading) { return 'LEGACY_STRUCTURED' }
    if ($HasDriftHeading -or $HasDriftLog) { return 'LEGACY_PARTIAL' }
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

function Test-GeneratedIgnoredPath {
    param([string]$RelativePath)

    $Path = $RelativePath.Replace('\', '/')
    if ($Path -match '(?i)(^|/)(node_modules|\.venv|venv|\.tox|vendor|dist|build|target|\.cache|\.next|coverage)(/|$)') {
        if ($Path -notmatch '(?i)drift|incident|inbox') {
            return $true
        }
    }

    return $false
}

function New-EvidenceCandidate {
    param(
        [string]$SourceState,
        [string]$CoverageOrigin,
        [string]$Repository,
        [string]$Origin,
        [string]$Branch,
        [string]$SourceCommit,
        [string]$RepositoryHeadContext,
        [string]$RelativePath,
        [string]$BlobSha,
        [string]$Sha256,
        [long]$Bytes,
        [bool]$WorktreeDirty,
        [string]$Text,
        [string]$PriorCandidateId = ''
    )

    $Assessment = Get-DiscoveryAssessment -RelativePath $RelativePath -Text $Text
    if (-not $Assessment.eligible) {
        return $null
    }

    $Model = Get-SourceModel -RepositoryName $Repository -RelativePath $RelativePath -Text $Text
    $TemplateFamily = Get-TemplateFamily -RepositoryName $Repository -RelativePath $RelativePath -Text $Text
    $TitleMatch = [regex]::Match($Text, '(?m)^#\s+(.+?)\s*$')
    $Title = if ($TitleMatch.Success) { $TitleMatch.Groups[1].Value.Trim() } else { [System.IO.Path]::GetFileNameWithoutExtension($RelativePath) }

    return [pscustomobject]@{
        combined_candidate_id = ''
        prior_candidate_id = $PriorCandidateId
        source_state = $SourceState
        coverage_origin = $CoverageOrigin
        source_repository = $Repository
        source_origin = $Origin
        source_branch = $Branch
        source_commit = $SourceCommit
        repository_head_context = $RepositoryHeadContext
        source_relative_path = $RelativePath.Replace('\', '/')
        source_git_blob_sha = $BlobSha
        source_sha256 = $Sha256
        source_bytes = $Bytes
        source_worktree_dirty = $WorktreeDirty
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
    }
}

Write-Stage 'DEFENSIVE DRIFT - M2 COMPREHENSIVE CORPUS AUDIT'
Write-Host ('Runtime: PowerShell {0} / {1}' -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)
Write-Host ('Git: {0}' -f $GitCommand.Source)
Write-Host 'Source repositories: READ ONLY'
Write-Host 'Remote-only repositories: shallow read cache only'
Write-Host 'Generated research artifacts: openai-defensive-drift-private only'

if (-not (Test-Path -LiteralPath $GitRoot -PathType Container)) { throw ('Git root not found: {0}' -f $GitRoot) }
if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) { throw ('Private repo not found: {0}' -f $PrivateRepo) }

Write-Host ''
Write-Host '[1/8] Sync private research workspace...'
$PrivateDirty = @(& git -C $PrivateRepo status --porcelain)
Assert-GitExit 'Read private status'
if ($PrivateDirty.Count -gt 0) {
    $PrivateDirty | ForEach-Object { Write-Host ('  ' + $_) }
    throw 'Private research workspace is not clean.'
}
& git -C $PrivateRepo pull --ff-only origin main
Assert-GitExit 'Sync private main'

$TrackedJson = Join-Path $PrivateRepo 'source-index\cross-model\drift-evidence-candidates.json'
$TrackedSnapshotsJson = Join-Path $PrivateRepo 'source-index\cross-model\source-repository-snapshots.json'
$GitHubSnapshotPath = Join-Path $PrivateRepo 'source-index\github-repository-snapshot-2026-08-30.txt'

foreach ($RequiredPath in @($TrackedJson, $TrackedSnapshotsJson, $GitHubSnapshotPath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw ('Required checkpoint artifact missing: {0}' -f $RequiredPath)
    }
}

$TrackedCheckpoint = @((Get-Content -LiteralPath $TrackedJson -Raw | ConvertFrom-Json))
$TrackedSnapshots = @((Get-Content -LiteralPath $TrackedSnapshotsJson -Raw | ConvertFrom-Json))
if ($TrackedCheckpoint.Count -lt 1900) {
    throw ('Tracked checkpoint unexpectedly contains only {0} candidates; expected at least 1900.' -f $TrackedCheckpoint.Count)
}
Write-Host ('  Preserved tracked checkpoint candidates: {0}' -f $TrackedCheckpoint.Count)

$GitHubRepos = @(
    Get-Content -LiteralPath $GitHubSnapshotPath |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and -not $_.StartsWith('#') }
)
Write-Host ('  GitHub repository snapshot entries: {0}' -f $GitHubRepos.Count)

$ExcludedRepositories = @('openai-defensive-drift', 'openai-defensive-drift-private')
$Combined = [System.Collections.Generic.List[object]]::new()

foreach ($Item in $TrackedCheckpoint) {
    $Combined.Add([pscustomobject]@{
        combined_candidate_id = ''
        prior_candidate_id = [string]$Item.candidate_id
        source_state = 'TRACKED_LOCAL_CHECKPOINT'
        coverage_origin = 'LOCAL_TRACKED_CHECKPOINT'
        source_repository = [string]$Item.source_repository
        source_origin = [string]$Item.source_origin
        source_branch = [string]$Item.source_branch
        source_commit = [string]$Item.source_commit
        repository_head_context = [string]$Item.source_commit
        source_relative_path = [string]$Item.source_relative_path
        source_git_blob_sha = [string]$Item.source_git_blob_sha
        source_sha256 = [string]$Item.source_sha256
        source_bytes = [long]$Item.source_bytes
        source_worktree_dirty = [bool]$Item.source_worktree_dirty
        source_model = [string]$Item.source_model
        model_confidence = [string]$Item.model_confidence
        model_provenance_raw = [string]$Item.model_provenance_raw
        template_family = [string]$Item.template_family
        discovery_score = [int]$Item.discovery_score
        discovery_signals = [string]$Item.discovery_signals
        title = [string]$Item.title
        drift_id_raw = [string]$Item.drift_id_raw
        severity_raw = [string]$Item.severity_raw
        affected_component_raw = [string]$Item.affected_component_raw
        recurrence_raw = [string]$Item.recurrence_raw
        review_status = 'UNREVIEWED'
        normalization_status = 'NOT_STARTED'
        proposed_case_id = ''
        notes = ''
    })
}

Write-Host ''
Write-Host '[2/8] Discover local source repositories and capture integrity snapshots...'
$LocalRepos = @(
    Get-ChildItem -LiteralPath $GitRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName '.git') -PathType Container } |
    Where-Object { $ExcludedRepositories -notcontains $_.Name } |
    Sort-Object Name
)
Write-Host ('  Local source repositories: {0}' -f $LocalRepos.Count)

$CheckpointHeadByRepo = @{}
foreach ($Snapshot in $TrackedSnapshots) {
    $CheckpointHeadByRepo[[string]$Snapshot.repository] = [string]$Snapshot.head
}

$IntegritySnapshots = [System.Collections.Generic.List[object]]::new()
foreach ($Repo in $LocalRepos) {
    $Head = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('rev-parse', 'HEAD')
    $Status = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('status', '--porcelain=v1', '--untracked-files=all')
    $IntegritySnapshots.Add([pscustomobject]@{
        repository = $Repo.Name
        path = $Repo.FullName
        head = $Head
        status = $Status
    })
}

Write-Host ''
Write-Host '[3/8] Scan local untracked and ignored Markdown evidence...'
$UntrackedScanned = 0
$IgnoredScanned = 0
$IgnoredGeneratedExcluded = 0
$LocalNewCandidates = 0
$OversizedExcluded = 0
$MaxBytes = 5MB

foreach ($Repo in $LocalRepos) {
    $Head = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('rev-parse', 'HEAD')
    $Origin = ''
    try { $Origin = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('remote', 'get-url', 'origin') } catch { $Origin = '' }
    $Branch = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('branch', '--show-current')
    $WorktreeDirty = -not [string]::IsNullOrWhiteSpace((Invoke-GitText -RepoPath $Repo.FullName -Arguments @('status', '--porcelain=v1')))

    $Untracked = @(Invoke-GitNullList -RepoPath $Repo.FullName -Arguments @('ls-files', '--others', '--exclude-standard', '-z', '--', '*.md'))
    $Ignored = @(Invoke-GitNullList -RepoPath $Repo.FullName -Arguments @('ls-files', '--others', '--ignored', '--exclude-standard', '-z', '--', '*.md'))

    Write-Host ('  {0}: untracked={1}, ignored={2}' -f $Repo.Name, $Untracked.Count, $Ignored.Count)

    foreach ($Entry in @(
        @($Untracked | ForEach-Object { [pscustomobject]@{ path = $_; state = 'UNTRACKED' } }) +
        @($Ignored | ForEach-Object { [pscustomobject]@{ path = $_; state = 'IGNORED_UNTRACKED' } })
    )) {
        $RelativePath = [string]$Entry.path
        $State = [string]$Entry.state

        if ($State -eq 'IGNORED_UNTRACKED' -and (Test-GeneratedIgnoredPath -RelativePath $RelativePath)) {
            $IgnoredGeneratedExcluded++
            continue
        }

        $FullPath = Join-Path $Repo.FullName ($RelativePath.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) { continue }

        $Info = Get-Item -LiteralPath $FullPath
        if ($Info.Length -gt $MaxBytes) {
            $OversizedExcluded++
            continue
        }

        $Text = [System.IO.File]::ReadAllText($FullPath)
        $Sha256 = (Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash.ToLowerInvariant()

        if ($State -eq 'UNTRACKED') { $UntrackedScanned++ } else { $IgnoredScanned++ }

        $Candidate = New-EvidenceCandidate `
            -SourceState $State `
            -CoverageOrigin 'LOCAL_WORKTREE' `
            -Repository $Repo.Name `
            -Origin $Origin `
            -Branch $Branch `
            -SourceCommit '' `
            -RepositoryHeadContext $Head `
            -RelativePath $RelativePath `
            -BlobSha '' `
            -Sha256 $Sha256 `
            -Bytes $Info.Length `
            -WorktreeDirty $WorktreeDirty `
            -Text $Text

        if ($null -ne $Candidate) {
            $Combined.Add($Candidate)
            $LocalNewCandidates++
        }
    }
}
Write-Host ('  Local untracked/ignored candidates added: {0}' -f $LocalNewCandidates)

Write-Host ''
Write-Host '[4/8] Scan tracked deltas since the preserved checkpoint...'
$TrackedDeltaFiles = 0
$TrackedDeltaCandidates = 0
foreach ($Repo in $LocalRepos) {
    $CurrentHead = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('rev-parse', 'HEAD')
    $OldHead = ''
    if ($CheckpointHeadByRepo.ContainsKey($Repo.Name)) { $OldHead = [string]$CheckpointHeadByRepo[$Repo.Name] }

    if ($OldHead -eq $CurrentHead) { continue }

    $Paths = @()
    if (-not [string]::IsNullOrWhiteSpace($OldHead)) {
        & git -C $Repo.FullName merge-base --is-ancestor $OldHead $CurrentHead 2>$null
        if ($LASTEXITCODE -eq 0) {
            $Paths = @(Invoke-GitNullList -RepoPath $Repo.FullName -Arguments @('diff', '--name-only', '--diff-filter=AM', '-z', $OldHead, $CurrentHead, '--', '*.md'))
        }
        else {
            $Paths = @(Invoke-GitNullList -RepoPath $Repo.FullName -Arguments @('ls-files', '-z', '--', '*.md'))
        }
    }
    else {
        $Paths = @(Invoke-GitNullList -RepoPath $Repo.FullName -Arguments @('ls-files', '-z', '--', '*.md'))
    }

    if ($Paths.Count -eq 0) { continue }
    Write-Host ('  {0}: tracked delta Markdown={1}' -f $Repo.Name, $Paths.Count)

    $Origin = ''
    try { $Origin = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('remote', 'get-url', 'origin') } catch { $Origin = '' }
    $Branch = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('branch', '--show-current')
    $WorktreeDirty = -not [string]::IsNullOrWhiteSpace((Invoke-GitText -RepoPath $Repo.FullName -Arguments @('status', '--porcelain=v1')))

    foreach ($RelativePath in $Paths) {
        $TrackedDeltaFiles++
        $FullPath = Join-Path $Repo.FullName ($RelativePath.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) { continue }

        $Info = Get-Item -LiteralPath $FullPath
        if ($Info.Length -gt $MaxBytes) { $OversizedExcluded++; continue }
        $Text = [System.IO.File]::ReadAllText($FullPath)
        $Sha256 = (Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $Spec = ('HEAD:{0}' -f $RelativePath.Replace('\', '/'))
        $BlobSha = Invoke-GitText -RepoPath $Repo.FullName -Arguments @('rev-parse', $Spec)

        $Candidate = New-EvidenceCandidate `
            -SourceState 'TRACKED_LOCAL_DELTA' `
            -CoverageOrigin 'LOCAL_TRACKED_DELTA' `
            -Repository $Repo.Name `
            -Origin $Origin `
            -Branch $Branch `
            -SourceCommit $CurrentHead `
            -RepositoryHeadContext $CurrentHead `
            -RelativePath $RelativePath `
            -BlobSha $BlobSha `
            -Sha256 $Sha256 `
            -Bytes $Info.Length `
            -WorktreeDirty $WorktreeDirty `
            -Text $Text

        if ($null -ne $Candidate) {
            $Combined.Add($Candidate)
            $TrackedDeltaCandidates++
        }
    }
}
Write-Host ('  Tracked delta candidates added: {0}' -f $TrackedDeltaCandidates)

Write-Host ''
Write-Host '[5/8] Compare local clones with the 65-repository GitHub snapshot...'
$LocalNameSet = @{}
foreach ($Repo in $LocalRepos) { $LocalNameSet[$Repo.Name.ToLowerInvariant()] = $true }

$MissingGitHubRepos = @(
    $GitHubRepos |
    Where-Object { $ExcludedRepositories -notcontains $_ } |
    Where-Object { -not $LocalNameSet.ContainsKey($_.ToLowerInvariant()) }
)
Write-Host ('  GitHub repositories absent from C:\GitHub and requiring remote tracked scan: {0}' -f $MissingGitHubRepos.Count)
$MissingGitHubRepos | ForEach-Object { Write-Host ('    ' + $_) }

Write-Host ''
Write-Host '[6/8] Scan tracked Markdown from GitHub-only repositories using shallow read cache...'
New-Item -ItemType Directory -Force -Path $CacheRoot | Out-Null
$RemoteMarkdownScanned = 0
$RemoteCandidates = 0
$RemoteRepoFailures = [System.Collections.Generic.List[string]]::new()

foreach ($RepoName in $MissingGitHubRepos) {
    $CachePath = Join-Path $CacheRoot $RepoName
    $CloneUrl = ('https://github.com/MikeHacksAI/{0}.git' -f $RepoName)
    Write-Host ('  Remote source: {0}' -f $RepoName)

    try {
        $Ref = 'HEAD'
        if (-not (Test-Path -LiteralPath (Join-Path $CachePath '.git') -PathType Container)) {
            if (Test-Path -LiteralPath $CachePath) {
                throw ('Cache path exists but is not a Git clone: {0}' -f $CachePath)
            }
            & git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 clone --depth 1 --filter=blob:none --no-checkout --no-tags $CloneUrl $CachePath
            Assert-GitExit ('Clone remote source ' + $RepoName)
            $Ref = 'HEAD'
        }
        else {
            & git -C $CachePath -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 fetch --depth 1 origin HEAD
            Assert-GitExit ('Refresh remote source cache ' + $RepoName)
            $Ref = 'FETCH_HEAD'
        }

        $Commit = Invoke-GitText -RepoPath $CachePath -Arguments @('rev-parse', $Ref)
        $Paths = @(Invoke-GitNullList -RepoPath $CachePath -Arguments @('ls-tree', '-r', '--name-only', '-z', $Ref, '--', '*.md'))
        Write-Host ('    tracked Markdown={0}' -f $Paths.Count)

        foreach ($RelativePath in $Paths) {
            $RemoteMarkdownScanned++
            $Spec = ('{0}:{1}' -f $Ref, $RelativePath.Replace('\', '/'))
            $BlobSha = Invoke-GitText -RepoPath $CachePath -Arguments @('rev-parse', $Spec)
            $ByteText = Invoke-GitText -RepoPath $CachePath -Arguments @('cat-file', '-s', $BlobSha)
            $Bytes = [long]$ByteText
            if ($Bytes -gt $MaxBytes) { $OversizedExcluded++; continue }
            $Text = Invoke-GitText -RepoPath $CachePath -Arguments @('show', $Spec)

            $Candidate = New-EvidenceCandidate `
                -SourceState 'TRACKED_REMOTE_CACHE' `
                -CoverageOrigin 'GITHUB_REMOTE' `
                -Repository $RepoName `
                -Origin $CloneUrl `
                -Branch 'REMOTE_DEFAULT' `
                -SourceCommit $Commit `
                -RepositoryHeadContext $Commit `
                -RelativePath $RelativePath `
                -BlobSha $BlobSha `
                -Sha256 '' `
                -Bytes $Bytes `
                -WorktreeDirty $false `
                -Text $Text

            if ($null -ne $Candidate) {
                $Combined.Add($Candidate)
                $RemoteCandidates++
            }
        }
    }
    catch {
        $RemoteRepoFailures.Add(('{0}: {1}' -f $RepoName, $_.Exception.Message))
        Write-Host ('    ERROR: {0}' -f $_.Exception.Message)
    }
}
Write-Host ('  Remote tracked candidates added: {0}' -f $RemoteCandidates)

Write-Host ''
Write-Host '[7/8] Verify original local source repositories were not modified...'
foreach ($Snapshot in $IntegritySnapshots) {
    $HeadAfter = Invoke-GitText -RepoPath $Snapshot.path -Arguments @('rev-parse', 'HEAD')
    $StatusAfter = Invoke-GitText -RepoPath $Snapshot.path -Arguments @('status', '--porcelain=v1', '--untracked-files=all')
    if ($HeadAfter -ne $Snapshot.head) { throw ('Source HEAD changed during audit: {0}' -f $Snapshot.repository) }
    if ($StatusAfter -ne $Snapshot.status) { throw ('Source worktree changed during audit: {0}' -f $Snapshot.repository) }
}
Write-Host '  SOURCE INTEGRITY CHECK: PASS'

for ($Index = 0; $Index -lt $Combined.Count; $Index++) {
    $Combined[$Index].combined_candidate_id = ('M2C-{0:D6}' -f ($Index + 1))
}

$OutputRoot = Join-Path $PrivateRepo 'source-index\comprehensive'
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$CombinedCsv = Join-Path $OutputRoot 'combined-drift-evidence-candidates.csv'
$CombinedJson = Join-Path $OutputRoot 'combined-drift-evidence-candidates.json'
$CoverageCsv = Join-Path $OutputRoot 'repository-coverage.csv'
$SummaryMd = Join-Path $OutputRoot 'coverage-summary.md'

$Combined | Export-Csv -LiteralPath $CombinedCsv -NoTypeInformation -Encoding utf8
$Combined | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $CombinedJson -Encoding utf8

$CoverageRows = [System.Collections.Generic.List[object]]::new()
foreach ($RepoName in $GitHubRepos) {
    $Excluded = $ExcludedRepositories -contains $RepoName
    $LocalPresent = $LocalNameSet.ContainsKey($RepoName.ToLowerInvariant())
    $RemoteFailure = @($RemoteRepoFailures | Where-Object { $_ -like ($RepoName + ':*') }).Count -gt 0
    $Disposition = if ($Excluded) { 'EXCLUDED_DEFENSIVE_DRIFT_OUTPUT_REPO' } elseif ($LocalPresent) { 'LOCAL_SOURCE_AUDITED' } elseif ($RemoteFailure) { 'REMOTE_SCAN_FAILED' } else { 'REMOTE_SOURCE_AUDITED' }
    $CoverageRows.Add([pscustomobject]@{
        repository = $RepoName
        local_clone_present = $LocalPresent
        disposition = $Disposition
    })
}
$CoverageRows | Export-Csv -LiteralPath $CoverageCsv -NoTypeInformation -Encoding utf8

$Summary = @(
    '# Defensive Drift M2 Comprehensive Corpus Coverage',
    '',
    ('Generated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')),
    '',
    '## Counts',
    '',
    ('- GitHub repository snapshot: **{0}**' -f $GitHubRepos.Count),
    ('- Local source repositories: **{0}**' -f $LocalRepos.Count),
    ('- Preserved tracked-checkpoint candidates: **{0}**' -f $TrackedCheckpoint.Count),
    ('- Local untracked Markdown scanned: **{0}**' -f $UntrackedScanned),
    ('- Local ignored Markdown scanned after generated-path exclusions: **{0}**' -f $IgnoredScanned),
    ('- Ignored generated/vendor Markdown explicitly excluded: **{0}**' -f $IgnoredGeneratedExcluded),
    ('- Tracked delta Markdown scanned: **{0}**' -f $TrackedDeltaFiles),
    ('- GitHub-only tracked Markdown scanned: **{0}**' -f $RemoteMarkdownScanned),
    ('- New local untracked/ignored candidates: **{0}**' -f $LocalNewCandidates),
    ('- New tracked-delta candidates: **{0}**' -f $TrackedDeltaCandidates),
    ('- New GitHub-remote candidates: **{0}**' -f $RemoteCandidates),
    ('- Combined candidate records: **{0}**' -f $Combined.Count),
    ('- Oversized Markdown explicitly excluded (>5 MiB): **{0}**' -f $OversizedExcluded),
    ('- Remote repository scan failures: **{0}**' -f $RemoteRepoFailures.Count),
    '',
    '## Corpus rules',
    '',
    '- Original local source repositories are read-only during this audit.',
    '- Git-tracked, untracked, and ignored user-authored Markdown can all qualify as evidence.',
    '- Ignored generated/vendor/cache Markdown is excluded unless its path itself signals drift/incident/inbox relevance.',
    '- GitHub repositories missing locally are scanned through a separate shallow read cache under `C:\DefensiveDrift\source-cache`.',
    '- Defensive Drift public/private output repositories are excluded as source evidence to avoid self-ingestion.',
    '- No evidence record is deleted or deduplicated away; provenance differences remain explicit.',
    '- Benchmark selection may not begin until repository coverage and any scan failures are reviewed.',
    ''
)

if ($RemoteRepoFailures.Count -gt 0) {
    $Summary += '## Remote scan failures'
    $Summary += ''
    foreach ($Failure in $RemoteRepoFailures) { $Summary += ('- ' + $Failure) }
    $Summary += ''
}

[System.IO.File]::WriteAllLines($SummaryMd, $Summary, [System.Text.UTF8Encoding]::new($false))
$CombinedHash = (Get-FileHash -LiteralPath $CombinedCsv -Algorithm SHA256).Hash.ToLowerInvariant()

Write-Host ''
Write-Host '[8/8] Commit comprehensive private corpus artifacts...'
& git -C $PrivateRepo add 'source-index/comprehensive'
Assert-GitExit 'Stage comprehensive corpus artifacts'
& git -C $PrivateRepo diff --cached --check
Assert-GitExit 'Validate comprehensive corpus artifacts'

$Staged = @(& git -C $PrivateRepo diff --cached --name-only)
Assert-GitExit 'Read staged comprehensive artifacts'
if ($Staged.Count -eq 0) { throw 'No comprehensive corpus artifacts were staged.' }

& git -C $PrivateRepo commit -m 'Complete M2 corpus coverage audit'
Assert-GitExit 'Commit comprehensive corpus audit'
& git -C $PrivateRepo push origin main
Assert-GitExit 'Push comprehensive corpus audit'
$PrivateHead = Invoke-GitText -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')

Write-Stage 'M2 COMPREHENSIVE CORPUS AUDIT FINISHED'
Write-Host ('CombinedCandidates={0}' -f $Combined.Count)
Write-Host ('CombinedInventorySHA256={0}' -f $CombinedHash)
Write-Host ('RemoteRepositoryFailures={0}' -f $RemoteRepoFailures.Count)
Write-Host ('PrivateCommit={0}' -f $PrivateHead)
Write-Host 'OriginalSourceRepositoriesModified=0'

if ($RemoteRepoFailures.Count -gt 0) {
    Write-Host 'FINAL STATUS: PARTIAL - review remote scan failures before benchmark selection.'
    exit 2
}

Write-Host 'FINAL STATUS: SUCCESS - corpus coverage audit complete; benchmark selection may proceed.'
exit 0
