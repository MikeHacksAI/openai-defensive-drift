[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:GIT_TERMINAL_PROMPT = '0'

$GitRoot     = 'C:\GitHub'
$PublicRepo  = Join-Path $GitRoot 'openai-defensive-drift'
$PrivateRepo = Join-Path $GitRoot 'openai-defensive-drift-private'
$DriftRepo   = Join-Path $GitRoot 'mikehacksai-drift-records'

$PrivateRemote = 'https://github.com/MikeHacksAI/openai-defensive-drift-private.git'
$DriftRemote   = 'https://github.com/MikeHacksAI/mikehacksai-drift-records.git'

function Write-Stage {
    param([string]$Text)
    Write-Host ''
    Write-Host '============================================================================'
    Write-Host " $Text"
    Write-Host " Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
    Write-Host '============================================================================'
}

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Invoke-GitNetwork {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)

    & git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git network operation failed: git $($GitArgs -join ' ')"
    }
}

function Write-Utf8NoBom {
    param(
        [string]$Base,
        [string]$RelativePath,
        [string]$Content
    )

    $FullPath = Join-Path $Base $RelativePath
    $Parent = Split-Path $FullPath -Parent

    if (-not (Test-Path $Parent)) {
        New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    }

    $Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($FullPath, $Content, $Utf8NoBom)
    Write-Host "  WROTE: $RelativePath"
}

function Get-OriginUrl {
    param([string]$RepoPath)
    $Value = (& git -C $RepoPath remote get-url origin).Trim()
    Assert-LastExitCode "Read origin for $RepoPath"
    return $Value
}

function Assert-Origin {
    param(
        [string]$RepoPath,
        [string]$ExpectedRepo
    )

    $Origin = Get-OriginUrl $RepoPath
    if ($Origin -notmatch "github\.com[/:]$([regex]::Escape($ExpectedRepo))(\.git)?$") {
        throw "Unexpected origin for $RepoPath. Expected $ExpectedRepo; found $Origin"
    }

    Write-Host "  ORIGIN VERIFIED: $ExpectedRepo"
}

function Assert-CleanWorkingTree {
    param([string]$RepoPath)

    $Dirty = @(& git -C $RepoPath status --porcelain)
    Assert-LastExitCode "git status for $RepoPath"

    if ($Dirty.Count -gt 0) {
        Write-Host ''
        Write-Host "UNCOMMITTED CHANGES DETECTED: $RepoPath"
        $Dirty | ForEach-Object { Write-Host "  $_" }
        throw 'Refusing to continue with an unclean working tree.'
    }
}

function Ensure-Repo {
    param(
        [string]$Path,
        [string]$Remote,
        [string]$ExpectedRepo
    )

    if (-not (Test-Path $Path)) {
        Write-Host "  CLONING: $ExpectedRepo"
        Invoke-GitNetwork clone $Remote $Path
    }

    if (-not (Test-Path (Join-Path $Path '.git'))) {
        throw "Path exists but is not a Git repository: $Path"
    }

    Assert-Origin -RepoPath $Path -ExpectedRepo $ExpectedRepo
    Assert-CleanWorkingTree -RepoPath $Path

    Invoke-GitNetwork -C $Path fetch origin

    & git -C $Path checkout main
    Assert-LastExitCode "Checkout main in $ExpectedRepo"

    Invoke-GitNetwork -C $Path pull --ff-only origin main

    Write-Host "  HEAD: $((& git -C $Path rev-parse HEAD).Trim())"
}

function Extract-Field {
    param(
        [string]$Text,
        [string]$Field
    )

    $Escaped = [regex]::Escape($Field)
    $Patterns = @(
        "(?mi)^\s*(?:[-*]\s*)?\*\*$Escaped:\*\*\s*(.+?)\s*$",
        "(?mi)^\s*(?:[-*]\s*)?$Escaped:\s*(.+?)\s*$"
    )

    foreach ($Pattern in $Patterns) {
        $Match = [regex]::Match($Text, $Pattern)
        if ($Match.Success) {
            return $Match.Groups[1].Value.Trim()
        }
    }

    return ''
}

function Get-GitBlobSha {
    param(
        [string]$RepoPath,
        [string]$RelativePath
    )

    $GitPath = $RelativePath.Replace('\', '/')
    $BlobSha = (& git -C $RepoPath rev-parse "HEAD:$GitPath" 2>$null).Trim()
    if ($LASTEXITCODE -ne 0) {
        return ''
    }

    return $BlobSha
}

Write-Stage 'DEFENSIVE DRIFT — M2 CANDIDATE INTAKE'

Write-Host '[1/8] Validate public repo state...'
if (-not (Test-Path (Join-Path $PublicRepo '.git'))) {
    throw "Public repository clone missing: $PublicRepo"
}
Assert-Origin -RepoPath $PublicRepo -ExpectedRepo 'MikeHacksAI/openai-defensive-drift'
Assert-CleanWorkingTree -RepoPath $PublicRepo
Write-Host "  PUBLIC HEAD: $((& git -C $PublicRepo rev-parse HEAD).Trim())"

Write-Host ''
Write-Host '[2/8] Clone/sync private research workspace...'
Ensure-Repo `
    -Path $PrivateRepo `
    -Remote $PrivateRemote `
    -ExpectedRepo 'MikeHacksAI/openai-defensive-drift-private'

Write-Host ''
Write-Host '[3/8] Clone/sync canonical drift evidence read-copy...'
Ensure-Repo `
    -Path $DriftRepo `
    -Remote $DriftRemote `
    -ExpectedRepo 'MikeHacksAI/mikehacksai-drift-records'

$SourceHeadBefore = (& git -C $DriftRepo rev-parse HEAD).Trim()
$SourceStatusBefore = ((& git -C $DriftRepo status --porcelain) -join "`n")
$SourceBranch = (& git -C $DriftRepo branch --show-current).Trim()

Write-Host ''
Write-Host '[4/8] Create private research boundary documents...'

Write-Utf8NoBom $PrivateRepo 'docs\data-boundary.md' @'
# Defensive Drift — Private/Public Data Boundary

## Canonical source evidence

Canonical raw drift evidence remains in:

`MikeHacksAI/mikehacksai-drift-records`

Original records are immutable research source evidence. They are never moved, renamed, deleted, overwritten, or rewritten by Defensive Drift.

## Private research workspace

`MikeHacksAI/openai-defensive-drift-private` may contain:

- source indexes;
- candidate-case references;
- private adjudication notes;
- derived working representations;
- sanitization staging;
- rejected cases;
- private grant notes.

## Public research repository

`MikeHacksAI/openai-defensive-drift` contains only material approved for public distribution.

## Required flow

canonical raw source
→ reference/index
→ derived private working representation
→ adjudication
→ sanitization
→ public-release review
→ approved public artifact

No canonical raw source artifact is promoted directly to the public repository.
'@

Write-Utf8NoBom $PrivateRepo 'docs\promotion-to-public.md' @'
# Defensive Drift — Promotion to Public

A candidate may enter the public benchmark only after every applicable gate passes.

## Gate 1 — Source provenance

Record:

- canonical source repository;
- source-relative path;
- source commit SHA;
- canonical Git blob SHA;
- local read-copy SHA-256;
- derived candidate identifier.

## Gate 2 — Human adjudication

Determine:

- relationship class;
- remediation state;
- severity;
- evidence support;
- dangerous-false-duplicate relevance;
- confidence.

## Gate 3 — Sanitization

Remove or transform sensitive material without changing the technical meaning of the case.

## Gate 4 — Safety review

Verify absence of:

- credentials;
- secrets;
- PII;
- confidential material;
- redistribution-restricted content;
- unnecessary private infrastructure details.

## Gate 5 — Ground-truth integrity

Confirm sanitization did not change the correct relationship classification.

## Gate 6 — Public approval

Only then may the case receive `PUBLIC_APPROVED`.

If sanitization would damage research value, keep the source case private and create a synthetic public analogue.
'@

Write-Utf8NoBom $PrivateRepo 'adjudication-working\candidate-cases\README.md' @'
# Candidate Cases

Private working area for Defensive Drift benchmark candidates.

Files here are derived research material only. Canonical raw drift records remain untouched in `MikeHacksAI/mikehacksai-drift-records`.
'@

Write-Utf8NoBom $PrivateRepo 'sanitization-staging\README.md' @'
# Sanitization Staging

Private staging area for derived candidate material undergoing public-release review.

Canonical raw evidence is never copied here as a replacement source of truth and is never modified in place.
'@

Write-Host ''
Write-Host '[5/8] Build immutable-source candidate index...'

$ConfirmedRoot = Join-Path $DriftRepo 'raw\confirmed-incidents'
if (-not (Test-Path $ConfirmedRoot)) {
    throw "Canonical confirmed-incidents path not found: $ConfirmedRoot"
}

$Files = @(
    Get-ChildItem -Path $ConfirmedRoot -File -Filter '*.md' -Recurse |
    Sort-Object FullName
)

if ($Files.Count -eq 0) {
    throw 'No confirmed drift incident files found.'
}

$Rows = [System.Collections.Generic.List[object]]::new()
$Counter = 0

foreach ($File in $Files) {
    $Counter++
    $Text = Get-Content $File.FullName -Raw
    $RelativePath = [System.IO.Path]::GetRelativePath($DriftRepo, $File.FullName)
    $LocalSha256 = (Get-FileHash -Path $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $BlobSha = Get-GitBlobSha -RepoPath $DriftRepo -RelativePath $RelativePath

    $RawFilenameMatch = [regex]::Match(
        $Text,
        '(?m)^DRIFT-[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}-SEV-[1-4]-[^\r\n]+\.md\s*$'
    )

    $RawFilename = if ($RawFilenameMatch.Success) {
        $RawFilenameMatch.Value.Trim()
    }
    else {
        $File.Name
    }

    $Rows.Add([pscustomobject]@{
        candidate_id               = ('SRC-{0:D4}' -f $Counter)
        source_repository          = 'MikeHacksAI/mikehacksai-drift-records'
        source_branch              = $SourceBranch
        source_commit              = $SourceHeadBefore
        source_relative_path       = $RelativePath.Replace('\', '/')
        source_git_blob_sha        = $BlobSha
        local_readcopy_sha256      = $LocalSha256
        source_bytes               = $File.Length
        raw_filename               = $RawFilename
        drift_id                   = Extract-Field $Text 'Drift ID'
        severity                   = Extract-Field $Text 'Severity'
        incident_occurred_at       = Extract-Field $Text 'Incident Occurred At'
        affected_component         = Extract-Field $Text 'Affected Component'
        recurrence_classification  = Extract-Field $Text 'Recurrence Classification'
        related_drift_ids          = Extract-Field $Text 'Related Drift IDs'
        detected_by                = Extract-Field $Text 'Detected By'
        logging_initiation         = Extract-Field $Text 'Logging Initiation'
        current_status             = Extract-Field $Text 'Current Status'
        review_status              = 'UNREVIEWED'
        proposed_relationship      = ''
        public_release_status      = 'PRIVATE_ONLY'
        proposed_case_id           = ''
        notes                      = ''
    })
}

$IndexDirectory = Join-Path $PrivateRepo 'source-index'
New-Item -ItemType Directory -Force -Path $IndexDirectory | Out-Null

$CsvPath = Join-Path $IndexDirectory 'drift-record-candidate-index.csv'
$JsonPath = Join-Path $IndexDirectory 'drift-record-candidate-index.json'

$Rows | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding utf8
$Rows | ConvertTo-Json -Depth 5 | Set-Content -Path $JsonPath -Encoding utf8

$IndexSha256 = (Get-FileHash -Path $CsvPath -Algorithm SHA256).Hash.ToLowerInvariant()

$SeveritySummary = @(
    $Rows |
    Group-Object severity |
    Sort-Object Count -Descending |
    ForEach-Object {
        [pscustomobject]@{
            severity = if ([string]::IsNullOrWhiteSpace($_.Name)) { '(missing)' } else { $_.Name }
            count = $_.Count
        }
    }
)

$Snapshot = [ordered]@{
    generated_at       = (Get-Date).ToString('o')
    source_repository  = 'MikeHacksAI/mikehacksai-drift-records'
    source_branch      = $SourceBranch
    source_commit      = $SourceHeadBefore
    indexed_root       = 'raw/confirmed-incidents'
    indexed_file_count = $Rows.Count
    csv_sha256         = $IndexSha256
}

Write-Utf8NoBom `
    $PrivateRepo `
    'source-index\source-snapshot.json' `
    ($Snapshot | ConvertTo-Json -Depth 5)

$SeverityLines = @(
    $SeveritySummary |
    ForEach-Object { "| $($_.severity -replace '\|','/') | $($_.count) |" }
) -join "`n"

$Summary = @"
# Defensive Drift — Source Candidate Inventory

Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')

## Source

- Repository: `MikeHacksAI/mikehacksai-drift-records`
- Branch: `$SourceBranch`
- Commit: `$SourceHeadBefore`
- Indexed root: `raw/confirmed-incidents`

## Inventory

- Confirmed Markdown records indexed: **$($Rows.Count)**
- Candidate CSV SHA-256: `$IndexSha256`

## Severity field distribution

| Severity field | Count |
|---|---:|
$SeverityLines

## Integrity statement

This operation created an index and private research working artifacts only.

No canonical raw incident file was moved, renamed, deleted, overwritten, or rewritten.
"@

Write-Utf8NoBom $PrivateRepo 'source-index\inventory-summary.md' $Summary

Write-Host "  INDEXED RECORDS: $($Rows.Count)"
Write-Host "  CSV SHA256:     $IndexSha256"

Write-Host ''
Write-Host '[6/8] Verify canonical drift source remained unchanged...'

$SourceHeadAfter = (& git -C $DriftRepo rev-parse HEAD).Trim()
$SourceStatusAfter = ((& git -C $DriftRepo status --porcelain) -join "`n")

if ($SourceHeadAfter -ne $SourceHeadBefore) {
    throw "Canonical source HEAD changed during indexing: $SourceHeadBefore -> $SourceHeadAfter"
}

if ($SourceStatusAfter -ne $SourceStatusBefore) {
    throw 'Canonical source working-tree state changed during indexing.'
}

Write-Host "  SOURCE HEAD UNCHANGED: $SourceHeadAfter"
Write-Host '  SOURCE WORKTREE UNCHANGED'
Write-Host '  RAW EVIDENCE PRESERVED'

Write-Host ''
Write-Host '[7/8] Validate and commit private M2 intake...'

& git -C $PrivateRepo status --short
Assert-LastExitCode 'Private git status'

& git -C $PrivateRepo add docs source-index adjudication-working sanitization-staging
Assert-LastExitCode 'Stage private M2 intake'

& git -C $PrivateRepo diff --cached --check
Assert-LastExitCode 'Private staged diff validation'

$Staged = @(& git -C $PrivateRepo diff --cached --name-only)
if ($Staged.Count -eq 0) {
    throw 'No private M2 artifacts were staged.'
}

& git -C $PrivateRepo commit -m 'Initialize M2 benchmark candidate intake'
Assert-LastExitCode 'Commit private M2 intake'

Invoke-GitNetwork -C $PrivateRepo push origin main

$PrivateHead = (& git -C $PrivateRepo rev-parse HEAD).Trim()

Write-Host ''
Write-Host '[8/8] Final verification...'
Assert-CleanWorkingTree -RepoPath $PrivateRepo
Assert-CleanWorkingTree -RepoPath $DriftRepo

Write-Stage 'M2 CANDIDATE INTAKE COMPLETE'
Write-Host " Source records indexed: $($Rows.Count)"
Write-Host " Source commit:          $SourceHeadBefore"
Write-Host " Private commit:         $PrivateHead"
Write-Host " Candidate index:        source-index/drift-record-candidate-index.csv"
Write-Host ' Canonical raw evidence: VERIFIED UNCHANGED'
