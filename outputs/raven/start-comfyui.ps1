param([switch]$Foreground)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$portable=Join-Path $PSScriptRoot '.runtime\comfyui\ComfyUI_windows_portable'
$python=Join-Path $portable 'python_embeded\python.exe'
$main=Join-Path $portable 'ComfyUI\main.py'
if(-not (Test-Path -LiteralPath $python)){throw 'ComfyUI portable Python is not installed.'}
if(-not (Test-Path -LiteralPath $main)){throw 'ComfyUI main.py is not installed.'}
$arguments=@(('"'+$main+'"'),'--listen','127.0.0.1','--port','8188','--lowvram','--disable-api-nodes','--disable-auto-launch','--preview-method','auto')
$listener=Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if(-not $listener){
  if($Foreground){& $python $main @($arguments[1..($arguments.Count-1)]);exit $LASTEXITCODE}
  $logDir=Join-Path $PSScriptRoot 'comfyui\logs'
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $portable -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'comfyui.out.log') -RedirectStandardError (Join-Path $logDir 'comfyui.err.log')
}
for($attempt=0;$attempt -lt 120;$attempt++){
  try{if((Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2).system){Write-Output 'ComfyUI is ready on http://127.0.0.1:8188';exit 0}}catch{}
  Start-Sleep -Seconds 1
}
throw 'ComfyUI did not become ready. Inspect comfyui/logs/comfyui.err.log.'
