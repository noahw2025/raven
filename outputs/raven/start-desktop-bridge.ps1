param([string]$Token='',[switch]$Foreground,[switch]$SkipRavenRestart)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$envPath=Join-Path $PSScriptRoot '.env'
if ([string]::IsNullOrWhiteSpace($Token)) {
  if(Test-Path -LiteralPath $envPath){
    $existing=Get-Content -LiteralPath $envPath | Where-Object {$_ -like 'DESKTOP_BRIDGE_TOKEN=*'} | Select-Object -First 1
    if($existing){$Token=$existing.Substring($existing.IndexOf('=')+1)}
  }
  if ([string]::IsNullOrWhiteSpace($Token)) {
    $bytes=New-Object byte[] 48
    $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $Token=[Convert]::ToBase64String($bytes)
  }
}
if ($Token.Length -lt 32) { throw 'Desktop bridge token must contain at least 32 characters.' }

# Synchronize the secret into Docker's server environment without printing it.
$lines=[System.Collections.Generic.List[string]]::new()
if(Test-Path -LiteralPath $envPath){$lines.AddRange([string[]](Get-Content -LiteralPath $envPath))}
function Set-RavenEnv([string]$Name,[string]$Value){
  for($i=0;$i -lt $lines.Count;$i++){if($lines[$i] -match ('^'+[regex]::Escape($Name)+'=')){ $lines[$i]="$Name=$Value";return }}
  $lines.Add("$Name=$Value")
}
Set-RavenEnv 'DESKTOP_BRIDGE_URL' 'http://host.docker.internal:8765'
Set-RavenEnv 'DESKTOP_BRIDGE_TOKEN' $Token
Set-RavenEnv 'DESKTOP_BRIDGE_ENABLED' 'true'
$projectsRoot=Join-Path $env:USERPROFILE 'Documents\Codex\RAVEN-Projects'
$configuredRoot=$lines | Where-Object {$_ -like 'RAVEN_PROJECTS_ROOT=*'} | Select-Object -First 1
if($configuredRoot){$projectsRoot=$configuredRoot.Substring($configuredRoot.IndexOf('=')+1)}else{Set-RavenEnv 'RAVEN_PROJECTS_ROOT' ($projectsRoot -replace '\\','/')}
[IO.File]::WriteAllLines($envPath,$lines,[Text.UTF8Encoding]::new($false))

$env:RAVEN_DESKTOP_BRIDGE_TOKEN=$Token
$env:RAVEN_DESKTOP_BRIDGE_BIND='127.0.0.1'
New-Item -ItemType Directory -Path $projectsRoot -Force | Out-Null
$env:RAVEN_PROJECTS_ROOT=$projectsRoot
$python=(Get-Command python -ErrorAction SilentlyContinue).Source
if(-not $python){$candidate=Join-Path $PSScriptRoot '..\..\work\raven-venv\Scripts\python.exe';if(Test-Path -LiteralPath $candidate){$python=(Resolve-Path -LiteralPath $candidate).Path}}
if(-not $python){$python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'}
if(-not (Test-Path -LiteralPath $python)){throw 'Python runtime not found.'}

$listener=Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if($listener){
  try{$existingHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -Headers @{Authorization="Bearer $Token"} -TimeoutSec 2}catch{$existingHealth=$null}
  if(-not $existingHealth.ok -or $existingHealth.version -ne '1.9'){
    $owner=Get-Process -Id ($listener | Select-Object -First 1 -ExpandProperty OwningProcess) -ErrorAction Stop
    $processInfo=Get-CimInstance Win32_Process -Filter "ProcessId=$($owner.Id)"
    if($owner.Path -notlike '*python*' -or $processInfo.CommandLine -notlike '*desktop_bridge.py*'){throw 'Port 8765 is not owned by the RAVEN companion; refusing to replace it.'}
    Stop-Process -Id $owner.Id -Force
    Start-Sleep -Milliseconds 500
    $listener=$null
  }
}
if(-not $listener){
  if($Foreground){& $python (Join-Path $PSScriptRoot 'desktop_bridge.py');exit $LASTEXITCODE}
  Start-Process -FilePath $python -ArgumentList ('"'+(Join-Path $PSScriptRoot 'desktop_bridge.py')+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}

if(-not $SkipRavenRestart){docker compose up -d --no-deps --force-recreate raven | Out-Null}
for($attempt=0;$attempt -lt 20;$attempt++){
  try{
    $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -Headers @{Authorization="Bearer $Token"} -TimeoutSec 2
    if($health.ok -and $health.version -eq '1.9'){
      if($SkipRavenRestart){Write-Output 'RAVEN desktop companion v1.9 is ready for Docker startup.';exit 0}
      for($ravenAttempt=0;$ravenAttempt -lt 30;$ravenAttempt++){
        try{$ravenHealth=Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/health' -TimeoutSec 2;if($ravenHealth.status -eq 'ok'){Write-Output 'RAVEN desktop companion v1.9 connected securely.';exit 0}}catch{}
        Start-Sleep -Milliseconds 500
      }
      throw 'Desktop companion is connected, but RAVEN did not become healthy on port 8080.'
    }
  }catch{Start-Sleep -Milliseconds 500}
}
throw 'Desktop companion did not become healthy on port 8765.'
