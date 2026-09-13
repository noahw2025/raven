$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    Write-Output 'Existing .env preserved.'
    exit 0
}

function New-RavenSecret([int]$bytes = 32) {
    $buffer = [byte[]]::new($bytes)
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($buffer) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($buffer) -replace '-', '').ToLowerInvariant()
}

$adminPassword = New-RavenSecret 12
$openAiKey = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Process')
if (-not $openAiKey) { $openAiKey = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'User') }
if (-not $openAiKey) { $openAiKey = '' }

$lines = @(
    "OPENAI_API_KEY=$openAiKey"
    "RAVEN_ADMIN_PASSWORD=$adminPassword"
    "RAVEN_JWT_SECRET=$(New-RavenSecret 48)"
    "POSTGRES_PASSWORD=$(New-RavenSecret 32)"
    'RAVEN_MODEL=gpt-4.1-mini'
    'RAVEN_EMBEDDING_MODEL=text-embedding-3-small'
    'RAVEN_REALTIME_MODEL=gpt-realtime-mini'
    'RAVEN_REALTIME_VOICE=marin'
    'RAVEN_MAX_CONTEXT_CHUNKS=6'
    'RAVEN_MAX_CONTEXT_CHARS=12000'
    'RAVEN_PUBLIC_ORIGIN=http://localhost:8080'
    'HERMES_URL='
    'HERMES_TOKEN='
)
[IO.File]::WriteAllLines($envPath, $lines, [Text.UTF8Encoding]::new($false))
Write-Output 'Created private .env. Credentials were not printed.'
Write-Output 'To sign in, read RAVEN_ADMIN_PASSWORD from .env locally.'
