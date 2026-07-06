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
$TempPattern = '^(com[0-9]+|tmp|wip|fixup|squash!|first|second|init)\b'

Write-Host "Scanning last $Count commits..."
Write-Host 'Standard format: type(scope): subject'
Write-Host ''

$commits = git log --format='%H %h %s' -n $Count
foreach ($line in $commits) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    $parts = $line -split ' ', 3
    if ($parts.Count -lt 3) { continue }

    $full = $parts[0]
    $short = $parts[1]
    $subject = $parts[2]
    $lower = $subject.ToLowerInvariant()
    $reasons = @()

    if ($subject -notmatch $StandardPattern) { $reasons += 'non-standard format' }
    if ($lower -match '^refact:') { $reasons += 'type typo (refact)' }
    if ($lower -match $TempPattern -or $lower -match '(^com[0-9]+ | com[0-9]+ |^com[0-9]+$)') { $reasons += 'temporary marker' }

    if ($reasons.Count -gt 0) {
        Write-Host "$short $full  [$($reasons -join '; ')]"
        Write-Host "  $subject"
        Write-Host ''
    }
}
