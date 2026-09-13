$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot

function Test-DockerEngine {
  $previousErrorActionPreference=$ErrorActionPreference
  $ErrorActionPreference='SilentlyContinue'
  try {
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  } finally {
    $ErrorActionPreference=$previousErrorActionPreference
  }
}

if(-not (Test-DockerEngine)){
  $dockerDesktop='C:\Program Files\Docker\Docker\Docker Desktop.exe'
  if(Test-Path -LiteralPath $dockerDesktop){
    Write-Output 'Docker Desktop is not ready. Starting it now...'
    Start-Process -FilePath $dockerDesktop
    for($attempt=0;$attempt -lt 45;$attempt++){
      Start-Sleep -Seconds 2
      if(Test-DockerEngine){break}
    }
  }
}
if(-not (Test-DockerEngine)){
  throw 'Docker Desktop did not start its Linux engine. Open Docker Desktop and resolve its displayed error. If it reports an inaccessible dockerInference socket, restart Windows once, then run this script again. RAVEN data is not deleted.'
}

& .\start-comfyui.ps1
# Generate/load the shared secret and start the host companion before Compose
# reads .env. A container cannot launch a Windows host process by itself.
& .\start-desktop-bridge.ps1 -SkipRavenRestart
docker compose up -d --build
if($LASTEXITCODE -ne 0){throw 'Docker Compose failed to start RAVEN.'}
for($attempt=0;$attempt -lt 60;$attempt++){
  try{$health=Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/health' -TimeoutSec 3;if($health.status -eq 'ok'){Write-Output 'RAVEN is ready at http://localhost:8080';exit 0}}catch{}
  Start-Sleep -Seconds 1
}
throw 'RAVEN did not become healthy after startup.'
