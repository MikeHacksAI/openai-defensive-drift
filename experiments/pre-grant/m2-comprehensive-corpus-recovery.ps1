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

function Write-Utf8Text {
    param(
        [string]$Path,
        [string]$Text
    )

    [System.IO.File]::WriteAllText(
        $Path,
        $Text,
        [System.Text.UTF8Encoding]::new($false)
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
    param([string]$Text)

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
    if (-not $Assessment.eligible) {
        return $null
    }

    $Model = Get-SourceModel -Text $Text
    $TemplateFamily = Get-TemplateFamily -Text $Text
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

function Get-PriorSummaryCount {
    param(
        [string]$SummaryText,
        [string]$Label
    )

    $Pattern = '(?m)^-\s+' + [regex]::Escape($Label) + ':\s+\*\*(\d+)\*\*\s*$'
    $Match = [regex]::Match($SummaryText, $Pattern)
    if ($Match.Success) {
        return [int]$Match.Groups[1].Value
    }

    return 0
}

Write-Stage 'DEFENSIVE DRIFT - M2 CORPUS RECOVERY'
Write-Host ('Runtime: PowerShell {0} / {1}' -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)
Write-Host ('Git: {0}' -f $GitCommand.Source)
Write-Host 'Recovery mode: reuse successful local/checkpoint output + existing remote cache'
Write-Host 'Original source repositories: NOT MODIFIED'

if (-not (Test-Path -LiteralPath $GitRoot -PathType Container)) { throw ('Git root not found: {0}' -f $GitRoot) }
if (-not (Test-Path -LiteralPath (Join-Path $PrivateRepo '.git') -PathType Container)) { throw ('Private repo not found: {0}' -f $PrivateRepo) }
if (-not (Test-Path -LiteralPath $CacheRoot -PathType Container)) { throw ('Remote cache root not found: {0}' -f $CacheRoot) }

$OutputRoot = Join-Path $PrivateRepo 'source-index\comprehensive'
$CombinedCsv = Join-Path $OutputRoot 'combined-drift-evidence-candidates.csv'
$CombinedJson = Join-Path $OutputRoot 'combined-drift-evidence-candidates.json'
$CoverageCsv = Join-Path $OutputRoot 'repository-coverage.csv'
$SummaryMd = Join-Path $OutputRoot 'coverage-summary.md'
$GitHubSnapshotPath = Join-Path $PrivateRepo 'source-index\github-repository-snapshot-2026-08-30.txt'

Write-Host ''
Write-Host '[1/6] Validate interrupted private workspace state...'

$DirtyPaths = [System.Collections.Generic.List[string]]::new()
foreach ($Path in @(Invoke-GitNullList -RepoPath $PrivateRepo -Arguments @('diff', '--cached', '--name-only', '-z'))) { $DirtyPaths.Add($Path) }
foreach ($Path in @(Invoke-GitNullList -RepoPath $PrivateRepo -Arguments @('diff', '--name-only', '-z'))) { $DirtyPaths.Add($Path) }
foreach ($Path in @(Invoke-GitNullList -RepoPath $PrivateRepo -Arguments @('ls-files', '--others', '--exclude-standard', '-z'))) { $DirtyPaths.Add($Path) }

$Unexpected = @(
    $DirtyPaths |
    Sort-Object -Unique |
    Where-Object { $_.Replace('\', '/') -notlike 'source-index/comprehensive/*' }
)

if ($Unexpected.Count -gt 0) {
    Write-Host '  Unexpected private changes:'
    $Unexpected | ForEach-Object { Write-Host ('    ' + $_) }
    throw 'Private workspace contains changes outside the interrupted comprehensive output. Nothing was changed.'
}

& git -C $PrivateRepo fetch origin main
Assert-GitExit 'Fetch private origin/main'
$PrivateHead = Invoke-GitText -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')
$PrivateRemoteHead = Invoke-GitText -RepoPath $PrivateRepo -Arguments @('rev-parse', 'origin/main')
if ($PrivateHead -ne $PrivateRemoteHead) {
    throw ('Private HEAD differs from origin/main. Local={0} Remote={1}' -f $PrivateHead, $PrivateRemoteHead)
}

& git -C $PrivateRepo reset --quiet -- 'source-index/comprehensive'
Assert-GitExit 'Unstage interrupted comprehensive artifacts'

foreach ($RequiredPath in @($CombinedJson, $CombinedCsv, $CoverageCsv, $SummaryMd, $GitHubSnapshotPath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw ('Required recovery artifact missing: {0}' -f $RequiredPath)
    }
}

$PriorSummaryText = [System.IO.File]::ReadAllText($SummaryMd)
$BaseCandidates = @((Get-Content -LiteralPath $CombinedJson -Raw | ConvertFrom-Json))
$ExistingRemoteCandidates = @($BaseCandidates | Where-Object { $_.coverage_origin -eq 'GITHUB_REMOTE' })
if ($ExistingRemoteCandidates.Count -ne 0) {
    throw ('Interrupted inventory unexpectedly contains {0} remote candidates; refusing to append duplicates.' -f $ExistingRemoteCandidates.Count)
}
if ($BaseCandidates.Count -lt 1900) {
    throw ('Interrupted inventory contains only {0} candidates; expected at least the 1900-candidate checkpoint.' -f $BaseCandidates.Count)
}

Write-Host ('  Preserved local/checkpoint candidate records: {0}' -f $BaseCandidates.Count)
Write-Host '  Interrupted comprehensive artifacts: PRESERVED IN PLACE, UNSTAGED'

Write-Host ''
Write-Host '[2/6] Resolve GitHub-only repositories from authoritative snapshot...'
$GitHubRepos = @(
    Get-Content -LiteralPath $GitHubSnapshotPath |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and -not $_.StartsWith('#') }
)
if ($GitHubRepos.Count -ne 65) {
    throw ('GitHub snapshot contains {0} repositories; expected 65.' -f $GitHubRepos.Count)
}

$ExcludedRepositories = @('openai-defensive-drift', 'openai-defensive-drift-private')
$LocalNameSet = @{}
Get-ChildItem -LiteralPath $GitRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName '.git') -PathType Container } |
    ForEach-Object { $LocalNameSet[$_.Name] = $true }

$RemoteRepos = @(
    $GitHubRepos |
    Where-Object { $ExcludedRepositories -notcontains $_ } |
    Where-Object { -not $LocalNameSet.ContainsKey($_) }
)
Write-Host ('  GitHub repository snapshot: {0}' -f $GitHubRepos.Count)
Write-Host ('  Remote-only repositories to repair/verify: {0}' -f $RemoteRepos.Count)
if ($RemoteRepos.Count -ne 40) {
    throw ('Remote-only repository count changed from the failed run. Expected 40, found {0}. Review scope before continuing.' -f $RemoteRepos.Count)
}

Write-Host ''
Write-Host '[3/6] Re-enumerate complete remote Git trees and filter Markdown in PowerShell...'
$Combined = [System.Collections.Generic.List[object]]::new()
foreach ($Item in $BaseCandidates) { $Combined.Add($Item) }

$RemoteMarkdownScanned = 0
$RemoteCandidatesAdded = 0
$OversizedExcluded = 0
$MaxBytes = 5MB
$EmptyRepos = @{}
$RemoteMarkdownCounts = @{}
$RemoteFailures = [System.Collections.Generic.List[object]]::new()

foreach ($RepoName in $RemoteRepos) {
    $CachePath = Join-Path $CacheRoot $RepoName
    $CloneUrl = ('https://github.com/MikeHacksAI/{0}.git' -f $RepoName)
    Write-Host ('  {0}' -f $RepoName)

    try {
        if (-not (Test-Path -LiteralPath (Join-Path $CachePath '.git') -PathType Container)) {
            throw ('Expected cache clone missing: {0}' -f $CachePath)
        }

        & git -C $CachePath rev-parse --verify HEAD *> $null
        $HasHead = ($LASTEXITCODE -eq 0)
        $Ref = 'HEAD'

        if (-not $HasHead) {
            $RemoteHeads = @(& git ls-remote --heads $CloneUrl 2>&1)
            if ($LASTEXITCODE -ne 0) {
                throw ('Unable to determine whether repository is empty: {0}' -f (($RemoteHeads | Out-String).Trim()))
            }

            if ($RemoteHeads.Count -eq 0) {
                $EmptyRepos[$RepoName] = $true
                $RemoteMarkdownCounts[$RepoName] = 0
                Write-Host '    EMPTY_REPOSITORY — covered, no commit tree to scan'
                continue
            }

            & git -C $CachePath fetch --depth 1 origin HEAD
            Assert-GitExit ('Fetch missing cache HEAD for ' + $RepoName)
            $Ref = 'FETCH_HEAD'
        }

        $Commit = Invoke-GitText -RepoPath $CachePath -Arguments @('rev-parse', $Ref)
        $Branch = 'REMOTE_DEFAULT'
        try {
            $ResolvedBranch = Invoke-GitText -RepoPath $CachePath -Arguments @('symbolic-ref', '--short', 'HEAD')
            if (-not [string]::IsNullOrWhiteSpace($ResolvedBranch)) { $Branch = $ResolvedBranch }
        }
        catch {
            $Branch = 'REMOTE_DEFAULT'
        }

        $AllTrackedPaths = @(Invoke-GitNullList -RepoPath $CachePath -Arguments @('ls-tree', '-r', '--name-only', '-z', $Ref))
        $MarkdownPaths = @(
            $AllTrackedPaths |
            Where-Object { $_.EndsWith('.md', [System.StringComparison]::OrdinalIgnoreCase) }
        )
        $RemoteMarkdownCounts[$RepoName] = $MarkdownPaths.Count
        Write-Host ('    tracked files={0}; Markdown={1}' -f $AllTrackedPaths.Count, $MarkdownPaths.Count)

        if ($RepoName -eq 'incubating-ideas') {
            $SentinelFound = @($MarkdownPaths | Where-Object { $_.Replace('\', '/') -eq 'UNFINISHED-WORK.md' }).Count -gt 0
            if (-not $SentinelFound) {
                throw 'Remote tree sentinel failed: incubating-ideas/UNFINISHED-WORK.md was independently verified on GitHub but is absent from decoded cache tree.'
            }
            Write-Host '    SENTINEL: PASS — UNFINISHED-WORK.md detected'
        }

        foreach ($RelativePath in $MarkdownPaths) {
            $RemoteMarkdownScanned++
            $Spec = ('{0}:{1}' -f $Ref, $RelativePath.Replace('\', '/'))
            $BlobSha = Invoke-GitText -RepoPath $CachePath -Arguments @('rev-parse', $Spec)
            $ByteText = Invoke-GitText -RepoPath $CachePath -Arguments @('cat-file', '-s', $BlobSha)
            $Bytes = [long]$ByteText
            if ($Bytes -gt $MaxBytes) {
                $OversizedExcluded++
                continue
            }

            $Text = Invoke-GitText -RepoPath $CachePath -Arguments @('cat-file', 'blob', $BlobSha)
            $CandidateArgs = @{
                Repository = $RepoName
                Origin = $CloneUrl
                Branch = $Branch
                Commit = $Commit
                RelativePath = $RelativePath
                BlobSha = $BlobSha
                Bytes = $Bytes
                Text = $Text
            }
            $Candidate = New-RemoteCandidate @CandidateArgs
            if ($null -ne $Candidate) {
                $Combined.Add($Candidate)
                $RemoteCandidatesAdded++
            }
        }
    }
    catch {
        $RemoteFailures.Add([pscustomobject]@{
            repository = $RepoName
            error = $_.Exception.Message
        })
        Write-Host ('    ERROR: {0}' -f $_.Exception.Message)
    }
}

$NonEmptyRemote = @($RemoteRepos | Where-Object { -not $EmptyRepos.ContainsKey($_) })
$NonEmptyWithMarkdown = @($NonEmptyRemote | Where-Object { $RemoteMarkdownCounts.ContainsKey($_) -and $RemoteMarkdownCounts[$_] -gt 0 })
if ($NonEmptyWithMarkdown.Count -eq 0) {
    throw 'Remote enumeration sanity check failed: no non-empty remote repository produced Markdown after full-tree filtering.'
}

Write-Host ('  Remote Markdown scanned: {0}' -f $RemoteMarkdownScanned)
Write-Host ('  Remote drift candidates added: {0}' -f $RemoteCandidatesAdded)
Write-Host ('  Empty repositories covered: {0}' -f $EmptyRepos.Count)
Write-Host ('  Remote scan failures: {0}' -f $RemoteFailures.Count)

Write-Host ''
Write-Host '[4/6] Rebuild combined inventory and coverage artifacts deterministically...'
for ($Index = 0; $Index -lt $Combined.Count; $Index++) {
    $Combined[$Index].combined_candidate_id = ('M2C-{0:D6}' -f ($Index + 1))
}

$CoverageRows = [System.Collections.Generic.List[object]]::new()
foreach ($RepoName in $GitHubRepos) {
    $Excluded = $ExcludedRepositories -contains $RepoName
    $LocalPresent = $LocalNameSet.ContainsKey($RepoName)
    $IsEmpty = $EmptyRepos.ContainsKey($RepoName)
    $Failure = @($RemoteFailures | Where-Object { $_.repository -eq $RepoName }).Count -gt 0

    $Disposition = if ($Excluded) {
        'EXCLUDED_DEFENSIVE_DRIFT_OUTPUT_REPO'
    }
    elseif ($LocalPresent) {
        'LOCAL_SOURCE_AUDITED'
    }
    elseif ($IsEmpty) {
        'EMPTY_REPOSITORY_NO_COMMIT_TREE'
    }
    elseif ($Failure) {
        'REMOTE_SCAN_FAILED'
    }
    else {
        'REMOTE_SOURCE_AUDITED'
    }

    $MarkdownCount = if ($RemoteMarkdownCounts.ContainsKey($RepoName)) { $RemoteMarkdownCounts[$RepoName] } else { '' }
    $CoverageRows.Add([pscustomobject]@{
        repository = $RepoName
        local_clone_present = $LocalPresent
        disposition = $Disposition
        remote_markdown_count = $MarkdownCount
    })
}

$PriorUntrackedScanned = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'Local untracked Markdown scanned'
$PriorIgnoredScanned = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'Local ignored Markdown scanned after generated-path exclusions'
$PriorIgnoredExcluded = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'Ignored generated/vendor Markdown explicitly excluded'
$PriorTrackedDeltaScanned = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'Tracked delta Markdown scanned'
$PriorLocalCandidates = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'New local untracked/ignored candidates'
$PriorDeltaCandidates = Get-PriorSummaryCount -SummaryText $PriorSummaryText -Label 'New tracked-delta candidates'

$SummaryLines = [System.Collections.Generic.List[string]]::new()
$SummaryLines.Add('# Defensive Drift M2 Comprehensive Corpus Coverage')
$SummaryLines.Add('')
$SummaryLines.Add(('Recovered: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')))
$SummaryLines.Add('')
$SummaryLines.Add('## Counts')
$SummaryLines.Add('')
$SummaryLines.Add(('- GitHub repository snapshot: **{0}**' -f $GitHubRepos.Count))
$SummaryLines.Add(('- Preserved local/checkpoint candidate records from interrupted run: **{0}**' -f $BaseCandidates.Count))
$SummaryLines.Add(('- Local untracked Markdown scanned in interrupted run: **{0}**' -f $PriorUntrackedScanned))
$SummaryLines.Add(('- Local ignored Markdown scanned in interrupted run: **{0}**' -f $PriorIgnoredScanned))
$SummaryLines.Add(('- Ignored generated/vendor Markdown excluded in interrupted run: **{0}**' -f $PriorIgnoredExcluded))
$SummaryLines.Add(('- Tracked delta Markdown scanned in interrupted run: **{0}**' -f $PriorTrackedDeltaScanned))
$SummaryLines.Add(('- Local untracked/ignored drift candidates contributed: **{0}**' -f $PriorLocalCandidates))
$SummaryLines.Add(('- Tracked-delta drift candidates contributed: **{0}**' -f $PriorDeltaCandidates))
$SummaryLines.Add(('- Remote-only repositories repaired/verified: **{0}**' -f $RemoteRepos.Count))
$SummaryLines.Add(('- Empty repositories with no commit tree: **{0}**' -f $EmptyRepos.Count))
$SummaryLines.Add(('- GitHub-only tracked Markdown scanned after full-tree repair: **{0}**' -f $RemoteMarkdownScanned))
$SummaryLines.Add(('- New GitHub-remote drift candidates: **{0}**' -f $RemoteCandidatesAdded))
$SummaryLines.Add(('- Combined candidate records: **{0}**' -f $Combined.Count))
$SummaryLines.Add(('- Oversized remote Markdown excluded (>5 MiB): **{0}**' -f $OversizedExcluded))
$SummaryLines.Add(('- Remote repository scan failures: **{0}**' -f $RemoteFailures.Count))
$SummaryLines.Add('')
$SummaryLines.Add('## Recovery validation')
$SummaryLines.Add('')
$SummaryLines.Add('- The successful local/checkpoint portion of the interrupted audit was preserved rather than rescanned.')
$SummaryLines.Add('- Remote repositories were read from the already-built shallow cache; no original local source repository was modified by recovery.')
$SummaryLines.Add('- Remote Markdown enumeration used the complete Git tree followed by case-insensitive `.md` filtering in PowerShell.')
$SummaryLines.Add('- `incubating-ideas/UNFINISHED-WORK.md` served as an independently verified remote-tree sentinel and had to be detected for recovery to continue.')
$SummaryLines.Add('- Repositories with no commit tree are classified as covered empty repositories rather than scan failures.')
$SummaryLines.Add('- Generated text is normalized to exactly one final newline before Git whitespace validation.')
$SummaryLines.Add('- Benchmark selection remains blocked if any true remote scan failure remains.')

if ($RemoteFailures.Count -gt 0) {
    $SummaryLines.Add('')
    $SummaryLines.Add('## Remote scan failures')
    $SummaryLines.Add('')
    foreach ($Failure in $RemoteFailures) {
        $SummaryLines.Add(('- **{0}:** {1}' -f $Failure.repository, $Failure.error))
    }
}

$CombinedCsvText = ((@($Combined) | ConvertTo-Csv -NoTypeInformation) -join "`n") + "`n"
$CombinedJsonText = (@($Combined) | ConvertTo-Json -Depth 7) + "`n"
$CoverageCsvText = ((@($CoverageRows) | ConvertTo-Csv -NoTypeInformation) -join "`n") + "`n"
$SummaryText = ($SummaryLines -join "`n") + "`n"

foreach ($Generated in @($CombinedCsvText, $CombinedJsonText, $CoverageCsvText, $SummaryText)) {
    if ($Generated.EndsWith("`n`n")) {
        throw 'Generated artifact preflight failed: trailing blank line detected before filesystem write.'
    }
}

Write-Utf8Text -Path $CombinedCsv -Text $CombinedCsvText
Write-Utf8Text -Path $CombinedJson -Text $CombinedJsonText
Write-Utf8Text -Path $CoverageCsv -Text $CoverageCsvText
Write-Utf8Text -Path $SummaryMd -Text $SummaryText

$CombinedHash = (Get-FileHash -LiteralPath $CombinedCsv -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host ('  Combined candidates: {0}' -f $Combined.Count)
Write-Host ('  Combined inventory SHA256: {0}' -f $CombinedHash)

Write-Host ''
Write-Host '[5/6] Validate and commit repaired private artifacts...'
$RelativeOutputs = @(
    'source-index/comprehensive/combined-drift-evidence-candidates.csv',
    'source-index/comprehensive/combined-drift-evidence-candidates.json',
    'source-index/comprehensive/repository-coverage.csv',
    'source-index/comprehensive/coverage-summary.md'
)

& git -C $PrivateRepo add -- @RelativeOutputs
Assert-GitExit 'Stage repaired comprehensive artifacts'

& git -C $PrivateRepo diff --cached --check
Assert-GitExit 'Validate repaired comprehensive artifacts'

$StagedPaths = @(Invoke-GitNullList -RepoPath $PrivateRepo -Arguments @('diff', '--cached', '--name-only', '-z'))
$UnexpectedStaged = @($StagedPaths | Where-Object { $RelativeOutputs -notcontains $_.Replace('\', '/') })
if ($UnexpectedStaged.Count -gt 0) {
    $UnexpectedStaged | ForEach-Object { Write-Host ('  UNEXPECTED STAGED: ' + $_) }
    throw 'Unexpected private artifacts are staged. Commit aborted.'
}
if ($StagedPaths.Count -eq 0) {
    throw 'No repaired comprehensive artifacts are staged.'
}

$CommitMessage = if ($RemoteFailures.Count -eq 0) {
    'Complete repaired M2 corpus coverage audit'
}
else {
    'Preserve partial repaired M2 corpus coverage audit'
}

& git -C $PrivateRepo commit -m $CommitMessage
Assert-GitExit 'Commit repaired comprehensive corpus artifacts'
& git -C $PrivateRepo push origin main
Assert-GitExit 'Push repaired comprehensive corpus artifacts'
$CommittedHead = Invoke-GitText -RepoPath $PrivateRepo -Arguments @('rev-parse', 'HEAD')

Write-Host ''
Write-Host '[6/6] Final verification...'
$FinalPrivateStatus = @(Invoke-GitNullList -RepoPath $PrivateRepo -Arguments @('status', '--porcelain=v1', '-z', '--untracked-files=all'))
if ($FinalPrivateStatus.Count -gt 0) {
    Write-Host '  WARNING: private workspace is not clean after commit:'
    $FinalPrivateStatus | ForEach-Object { Write-Host ('    ' + $_) }
    throw 'Private workspace not clean after recovery commit.'
}

Write-Stage 'M2 CORPUS RECOVERY FINISHED'
Write-Host ('CombinedCandidates={0}' -f $Combined.Count)
Write-Host ('RemoteMarkdownScanned={0}' -f $RemoteMarkdownScanned)
Write-Host ('RemoteCandidatesAdded={0}' -f $RemoteCandidatesAdded)
Write-Host ('EmptyRepositories={0}' -f $EmptyRepos.Count)
Write-Host ('RemoteFailures={0}' -f $RemoteFailures.Count)
Write-Host ('CombinedInventorySHA256={0}' -f $CombinedHash)
Write-Host ('PrivateCommit={0}' -f $CommittedHead)
Write-Host 'OriginalSourceRepositoriesModifiedByRecovery=0'

if ($RemoteFailures.Count -gt 0) {
    Write-Host 'FINAL STATUS: PARTIAL — true remote failures remain; benchmark selection is blocked.'
    exit 2
}

Write-Host 'FINAL STATUS: SUCCESS — comprehensive corpus coverage repaired and committed.'
exit 0
