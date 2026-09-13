$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
Write-Host 'OpenRouter will receive research prompts and career/content inputs. Voice stays local.'
Write-Host 'Only free model routes are enabled; free quotas and availability still apply.'
$secureKey=Read-Host 'OpenRouter API key (hidden; saved server-side)' -AsSecureString
$pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
  $key=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  if([string]::IsNullOrWhiteSpace($key) -or $key.Contains("`n") -or $key.Contains("`r")){throw 'Invalid key'}
  $target=Join-Path $PSScriptRoot '.env'
  $lines=[Collections.Generic.List[string]]::new()
  if(Test-Path -LiteralPath $target){$lines.AddRange([string[]](Get-Content -LiteralPath $target))}
  $values=@{OPENROUTER_API_KEY=$key;OPENROUTER_MODEL='nvidia/nemotron-3-super-120b-a12b:free';RAVEN_RESEARCH_PROVIDER='openrouter';CONTENT_TEXT_PROVIDER='openrouter'}
  foreach($name in $values.Keys){
    $found=$false
    for($i=0;$i -lt $lines.Count;$i++){if($lines[$i].StartsWith($name+'=')){$lines[$i]=$name+'='+$values[$name];$found=$true}}
    if(-not $found){$lines.Add($name+'='+$values[$name])}
  }
  [IO.File]::WriteAllLines($target,$lines,[Text.UTF8Encoding]::new($false))
} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer);$key=$null}
docker compose up -d --no-deps --force-recreate raven hermes
if($LASTEXITCODE -ne 0){throw 'Key saved, but container restart failed. Start Docker Desktop and retry.'}
Write-Host 'Saved without displaying the key. Check Capabilities > Hermes Tools for readiness.'
