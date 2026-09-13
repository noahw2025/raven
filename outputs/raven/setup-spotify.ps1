param(
  [string]$ClientId='',
  [string]$RedirectUri='http://127.0.0.1:8766/callback'
)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$envPath=Join-Path $PSScriptRoot '.env'
$saved=@{}
if(Test-Path -LiteralPath $envPath){
  foreach($line in Get-Content -LiteralPath $envPath){
    if($line -match '^([^#=]+)=(.*)$'){$saved[$matches[1]]=$matches[2]}
  }
}

Write-Output 'Before continuing, add this exact Redirect URI to your Spotify developer app:'
Write-Output $RedirectUri
if([string]::IsNullOrWhiteSpace($ClientId) -and $saved.ContainsKey('SPOTIFY_CLIENT_ID')){$ClientId=$saved['SPOTIFY_CLIENT_ID']}
if([string]::IsNullOrWhiteSpace($ClientId)){$ClientId=Read-Host 'Spotify Client ID'}
if([string]::IsNullOrWhiteSpace($ClientId)){throw 'Spotify Client ID is required.'}
if($saved.ContainsKey('SPOTIFY_CLIENT_SECRET')){$ClientSecret=$saved['SPOTIFY_CLIENT_SECRET']}
else{
  $secretValue=Read-Host 'Spotify Client Secret (stored server-side only)' -AsSecureString
  $secretPtr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretValue)
  try{$ClientSecret=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPtr)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPtr)}
}
if([string]::IsNullOrWhiteSpace($ClientSecret)){throw 'Spotify Client Secret is required.'}

$stateBytes=New-Object byte[] 32
$rng=[Security.Cryptography.RandomNumberGenerator]::Create()
try{$rng.GetBytes($stateBytes)}finally{$rng.Dispose()}
# Windows PowerShell 5.1 runs on .NET Framework, which does not provide
# Convert.ToHexString. Format the cryptographically random state byte-by-byte
# so the helper works in both Windows PowerShell 5.1 and PowerShell 7+.
$state=-join ($stateBytes | ForEach-Object { $_.ToString('x2') })
$scope='user-modify-playback-state user-read-playback-state user-read-currently-playing user-library-read'
$authorize='https://accounts.spotify.com/authorize?response_type=code&client_id='+[Uri]::EscapeDataString($ClientId)+'&scope='+[Uri]::EscapeDataString($scope)+'&redirect_uri='+[Uri]::EscapeDataString($RedirectUri)+'&state='+$state

$listener=[Net.HttpListener]::new()
$listener.Prefixes.Add('http://127.0.0.1:8766/')
$listener.Start()
try{
  Start-Process $authorize
  Write-Output 'Complete Spotify authorization in the browser. Waiting for the local callback...'
  $context=$listener.GetContext()
  $query=$context.Request.QueryString
  $html='<html><body style="font-family:sans-serif;background:#071313;color:#d9fffa;padding:40px"><h2>Spotify authorization received</h2><p>You may close this tab and return to RAVEN.</p></body></html>'
  $bytes=[Text.Encoding]::UTF8.GetBytes($html)
  $context.Response.ContentType='text/html; charset=utf-8';$context.Response.ContentLength64=$bytes.Length
  $context.Response.OutputStream.Write($bytes,0,$bytes.Length);$context.Response.Close()
  if($query['state'] -ne $state){throw 'Spotify OAuth state validation failed.'}
  if($query['error']){throw "Spotify authorization was rejected: $($query['error'])"}
  $code=$query['code'];if([string]::IsNullOrWhiteSpace($code)){throw 'Spotify did not return an authorization code.'}
}finally{$listener.Stop();$listener.Close()}

$basic=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${ClientId}:${ClientSecret}"))
$token=Invoke-RestMethod -Uri 'https://accounts.spotify.com/api/token' -Method Post -Headers @{Authorization="Basic $basic"} -ContentType 'application/x-www-form-urlencoded' -Body @{grant_type='authorization_code';code=$code;redirect_uri=$RedirectUri}
if([string]::IsNullOrWhiteSpace($token.refresh_token)){throw 'Spotify did not return a refresh token.'}

$lines=[Collections.Generic.List[string]]::new()
if(Test-Path -LiteralPath $envPath){$lines.AddRange([string[]](Get-Content -LiteralPath $envPath))}
function Set-RavenEnv([string]$Name,[string]$Value){
  for($i=0;$i -lt $lines.Count;$i++){if($lines[$i] -match ('^'+[regex]::Escape($Name)+'=')){$lines[$i]="$Name=$Value";return}}
  $lines.Add("$Name=$Value")
}
Set-RavenEnv 'SPOTIFY_CLIENT_ID' $ClientId
Set-RavenEnv 'SPOTIFY_CLIENT_SECRET' $ClientSecret
Set-RavenEnv 'SPOTIFY_REFRESH_TOKEN' ([string]$token.refresh_token)
Set-RavenEnv 'SPOTIFY_PLAYBACK_ENABLED' 'true'
[IO.File]::WriteAllLines($envPath,$lines,[Text.UTF8Encoding]::new($false))
$ClientSecret=$null;$token=$null;$basic=$null

docker compose up -d --force-recreate raven | Out-Null
if($LASTEXITCODE -ne 0){throw 'Spotify was authorized, but RAVEN failed to restart.'}
Write-Output 'Spotify Premium playback and saved-library control are authorized server-side. Open Spotify on an active device, then ask RAVEN to play a track or your Liked Songs.'
