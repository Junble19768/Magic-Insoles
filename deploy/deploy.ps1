# magic-insoles one-click deploy (local build + scp sync + remote restart)

# Backend: backend_prod/ (default) or backend/ test stub (-FakeBackend)

# Usage: .\deploy\deploy.ps1

#        .\deploy\deploy.ps1 -Server root@47.76.112.33 -SkipBuild

#        .\deploy\deploy.ps1 -FakeBackend -BackendOnly



param(

    [string]$Server = "root@47.76.112.33",

    [string]$RemoteRoot = "/var/www/magic-insoles",

    [string]$BackendDir = "backend_prod",

    [string]$FrontDist = "/var/www/insoles/dist",

    [switch]$SkipBuild,

    [switch]$FrontendOnly,

    [switch]$BackendOnly,

    [switch]$FakeBackend

)



if ($FakeBackend) {

    $BackendDir = "backend"

}



$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot

$RemoteBackend = "$RemoteRoot/$BackendDir"



function Invoke-Step {

    param([string]$Message, [scriptblock]$Action)

    Write-Host ""

    Write-Host ">>> $Message" -ForegroundColor Cyan

    & $Action

    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {

        throw "Step failed: $Message (exit $LASTEXITCODE)"

    }

}



if (-not $BackendOnly) {

    if (-not $SkipBuild) {

        Invoke-Step "Building frontend..." {

            Push-Location (Join-Path $Root "frontend")

            try {

                npm run build

            } finally {

                Pop-Location

            }

        }

    } else {

        $distPath = Join-Path $Root "frontend\dist"

        if (-not (Test-Path $distPath)) {

            throw "frontend/dist not found. Run without -SkipBuild first."

        }

    }



    Invoke-Step "Syncing frontend dist to ${Server}:${FrontDist} ..." {

        ssh $Server "mkdir -p $FrontDist"

        scp -r (Join-Path $Root "frontend\dist\*") "${Server}:${FrontDist}/"

        ssh $Server "chmod -R a+rX $FrontDist"

    }

}



if (-not $FrontendOnly) {

    Invoke-Step "Syncing ${BackendDir} to ${Server}:${RemoteBackend} ..." {

        ssh $Server "mkdir -p $RemoteBackend"

        scp -r (Join-Path $Root "$BackendDir\*") "${Server}:${RemoteBackend}/"

    }



    $serviceFile = if ($FakeBackend) {

        "magic-insoles-api-fake.service"

    } else {

        "magic-insoles-api.service"

    }



    Invoke-Step "Updating systemd unit ($serviceFile)..." {

        scp (Join-Path $PSScriptRoot $serviceFile) "${Server}:/etc/systemd/system/magic-insoles-api.service"

    }



    Invoke-Step "Installing deps and restarting API..." {

        $remoteCmd = "set -e && cd $RemoteRoot && " +

            "([ -d venv ] || python3 -m venv venv) && " +

            "source venv/bin/activate && " +

            "pip install -q -r $BackendDir/requirements.txt && " +

            "mkdir -p $BackendDir/data && " +

            "if [ ! -f $BackendDir/.env ] && [ -f $BackendDir/.env.example ]; then cp $BackendDir/.env.example $BackendDir/.env; fi && " +

            "chown -R root:www-data $RemoteRoot && " +

            "chmod -R g+rX $RemoteRoot && " +

            "chown -R www-data:www-data $BackendDir/data && " +

            "systemctl daemon-reload && " +

            "systemctl restart magic-insoles-api && " +

            "systemctl is-active magic-insoles-api"

        ssh $Server $remoteCmd

    }

}



Write-Host ""

$backendLabel = if ($FakeBackend) { "fake stub (backend/)" } else { "production (backend_prod/)" }



Write-Host "Deploy complete." -ForegroundColor Green

Write-Host "  Backend:  $backendLabel"

Write-Host "  Frontend: http://47.76.112.33/insoles/"

Write-Host "  API:      http://47.76.112.33/api/activity/today"

Write-Host "  Health:   http://47.76.112.33/health"

if (-not $FakeBackend) {

    Write-Host "  Device TCP: port 9000 (ensure security group allows if needed)"

}


