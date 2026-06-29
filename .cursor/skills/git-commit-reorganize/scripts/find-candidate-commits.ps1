# List recent commits that are non-standard or look temporary.
# Usage: find-candidate-commits.ps1 [-Count 30]
param(
    [int]$Count = 30
)

$ErrorActionPreference = 'Stop'

$Root = git rev-parse --show-toplevel 2>$null
if (-not $Root) {
    $Root = (Get-Location).Path
}
Set-Location $Root

$ValidTypes = @('feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore')
$StandardPattern = '^(' + ($ValidTypes -join '|') + ')(\([^)]*\))?: .+'
$PlaceholderPattern = '^(first|second|init)$'
$TempPrefixPattern = '^(com[0-9]+|tmp|wip|fixup|squash!)'
$TempInlinePattern = '(^com[0-9]+ | com[0-9]+ |^com[0-9]+$)'

function Get-SuggestHint {
    param([string]$Subject)

    $lower = $Subject.ToLowerInvariant()

    if ($lower -match '^refact:') {
        return 'refactor(?): fix type spelling'
    }
    if ($lower -eq 'doc') {
        return 'docs(?): add subject verb'
    }
    if ($lower -match $PlaceholderPattern) {
        return 'squash into themed commit'
    }
    if ($lower -match $TempPrefixPattern -or $lower -match $TempInlinePattern) {
        return 'squash into themed commit'
    }
    if ($Subject -notmatch $StandardPattern) {
        return 'type(scope): subject'
    }
    return ''
}

Write-Host "Scanning last $Count commits..."
Write-Host 'Standard format: type(scope): subject'
Write-Host 'Allowed types: feat, fix, docs, style, refactor, test, chore'
Write-Host ''

$commits = git log --format='%H %h %s' -n $Count
foreach ($line in $commits) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    $parts = $line -split ' ', 3
    if ($parts.Count -lt 3) {
        continue
    }

    $full = $parts[0]
    $short = $parts[1]
    $subject = $parts[2]
    $lowerSubject = $subject.ToLowerInvariant()
    $reasons = @()

    if ($subject -notmatch $StandardPattern) {
        $reasons += 'non-standard format'
    }
    if ($lowerSubject -match '^refact:') {
        $reasons += 'type typo (refact)'
    }
    if ($lowerSubject -eq 'doc') {
        $reasons += 'single-word subject'
    }
    if ($lowerSubject -match $PlaceholderPattern) {
        $reasons += 'placeholder subject'
    }
    if ($lowerSubject -match $TempPrefixPattern) {
        $reasons += 'temporary marker'
    }
    if ($lowerSubject -match $TempInlinePattern) {
        $reasons += 'comN pattern'
    }

    if ($reasons.Count -eq 0) {
        continue
    }

    $reason = $reasons -join '; '
    $hint = Get-SuggestHint -Subject $subject

    Write-Host "$short $full  [$reason]"
    Write-Host "  $subject"
    if ($hint) {
        Write-Host "  hint: $hint"
    }
    Write-Host ''
}
