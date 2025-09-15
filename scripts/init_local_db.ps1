param(
    [string]$EnvFile = ".env",
    [int]$TimeoutSeconds = 120
)

# Load .env if exists
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+?)\s*=\s*(.+)\s*$") {
            $name = $matches[1].Trim()
            $raw = $matches[2].Trim()
            if ($raw.StartsWith('"') -and $raw.EndsWith('"')) {
                $value = $raw.Trim('"')
            } elseif ($raw.StartsWith("'") -and $raw.EndsWith("'")) {
                $value = $raw.Trim("'")
            } else {
                $value = $raw
            }
            Write-Host "Setting env $name"
            $env:$name = $value
        }
    }
}

Write-Host "Starting Postgres (docker-compose db)..."
docker compose up -d db

Write-Host "Waiting for Postgres to be ready (pg_isready)..."
$start = Get-Date
while ($true) {
    try {
        $check = docker exec -i $(docker ps -q -f "name=db") pg_isready -U $env:POSTGRES_USER -d $env:POSTGRES_DB
        if ($check -match "accepting connections") {
            Write-Host "Postgres is ready"
            break
        }
    } catch {
        # ignore and retry
    }
    if ((Get-Date) - $start).TotalSeconds -gt $TimeoutSeconds {
        Write-Error "Timed out waiting for Postgres after $TimeoutSeconds seconds"
        exit 1
    }
    Start-Sleep -Seconds 2
}

if (-not $env:DATABASE_URL) {
    # Build default DATABASE_URL from compose env if present
    if ($env:POSTGRES_USER -and $env:POSTGRES_PASSWORD -and $env:POSTGRES_DB) {
        $env:DATABASE_URL = "postgresql://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@localhost:5432/$($env:POSTGRES_DB)"
        Write-Host "Using DATABASE_URL=$env:DATABASE_URL"
    } else {
        Write-Host "DATABASE_URL not set and POSTGRES_* env vars not found; using sqlite fallback"
    }
}

Write-Host "Running alembic upgrade head..."
alembic upgrade head

Write-Host "Done."
