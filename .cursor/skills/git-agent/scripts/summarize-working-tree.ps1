# Summarize uncommitted changes grouped by module scope.
# Usage: summarize-working-tree.ps1 [-Paths path1,path2,...]
param(
    [string[]]$Paths = @()
)

$ErrorActionPreference = 'Stop'

$Root = git rev-parse --show-toplevel 2>$null
if (-not $Root) {
    $Root = (Get-Location).Path
}
Set-Location $Root

function Get-Scope {
    param([string]$File)

    switch -Wildcard ($File) {
        'backend/*' { return 'backend' }
        'frontend/*' { return 'frontend' }
        '3rdparty/*' { return '3rdparty' }
        'docs/*' { return 'docs' }
        '.cursor/*' { return 'cursor' }
        '.github/*' { return 'chore' }
        '*.yml' { return 'chore' }
        '*.yaml' { return 'chore' }
        'config.yml' { return 'config' }
        '.gitignore' { return 'chore' }
        default { return 'chore' }
    }
}

function Get-StageLabel {
    param([string]$IndexStatus, [string]$WorktreeStatus)

    $parts = @()
    if ($IndexStatus -ne ' ' -and $IndexStatus -ne '?') { $parts += 'staged' }
    if ($WorktreeStatus -ne ' ') { $parts += 'unstaged' }
    if ($IndexStatus -eq '?' -and $WorktreeStatus -eq '?') { $parts = @('untracked') }
    return ($parts -join ' + ')
}

$groups = @{}
$lines = git status --porcelain

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    $indexStatus = $line.Substring(0, 1)
    $worktreeStatus = $line.Substring(1, 1)
    $file = $line.Substring(3).Trim('"')

    if ($Paths.Count -gt 0) {
        $matched = $false
        foreach ($prefix in $Paths) {
            if ($file.StartsWith($prefix)) { $matched = $true; break }
        }
        if (-not $matched) { continue }
    }

    $scope = Get-Scope -File $file
    $stage = Get-StageLabel -IndexStatus $indexStatus -WorktreeStatus $worktreeStatus
    $entry = "  [$stage] $file"

    if ($groups.ContainsKey($scope)) { $groups[$scope] += "`n$entry" }
    else { $groups[$scope] = $entry }
}

if ($groups.Count -eq 0) {
    Write-Host 'No uncommitted changes found.'
    exit 0
}

Write-Host 'Working tree summary (grouped by scope):'
Write-Host ''

$order = @('backend', 'frontend', '3rdparty', 'docs', 'cursor', 'config', 'chore')
foreach ($scope in $order) {
    if ($groups.ContainsKey($scope)) {
        Write-Host "[$scope]"
        Write-Host $groups[$scope]
        Write-Host ''
        $groups.Remove($scope) | Out-Null
    }
}

foreach ($scope in ($groups.Keys | Sort-Object)) {
    Write-Host "[$scope]"
    Write-Host $groups[$scope]
    Write-Host ''
}
