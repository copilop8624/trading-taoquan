# Script to organize trading data files
Write-Host "Starting data organization..." -ForegroundColor Green

# Get current directory
$rootPath = Get-Location
$candlesPath = Join-Path $rootPath "candles"
$tradelistPath = Join-Path $rootPath "tradelist"

Write-Host "Root directory: $rootPath" -ForegroundColor Cyan
Write-Host "Candles directory: $candlesPath" -ForegroundColor Yellow
Write-Host "Tradelist directory: $tradelistPath" -ForegroundColor Yellow

# Create directories if they don't exist
if (-not (Test-Path $candlesPath)) {
    New-Item -ItemType Directory -Path $candlesPath -Force
    Write-Host "Created candles directory" -ForegroundColor Green
}

if (-not (Test-Path $tradelistPath)) {
    New-Item -ItemType Directory -Path $tradelistPath -Force
    Write-Host "Created tradelist directory" -ForegroundColor Green
}

Write-Host "`nScanning CSV files..." -ForegroundColor Cyan

# Get all CSV files in root directory
$csvFiles = Get-ChildItem -Path $rootPath -Name "*.csv" | Where-Object { 
    $_ -notlike "*\*" -and (Test-Path (Join-Path $rootPath $_)) 
}

$candleFiles = @()
$tradelistFiles = @()

# Classify files
foreach ($file in $csvFiles) {
    $fileName = $file.ToLower()
    
    # Check for candle files (OHLCV data)
    if ($fileName -match "binance.*\.(csv)$" -and 
        ($fileName -match "\d+\.csv$" -or $fileName -match ", \d+\.csv$")) {
        $candleFiles += $file
    }
    # Check for tradelist files
    elseif ($fileName -match "tradelist" -or 
            $fileName -match "trade.*list" -or
            $fileName -match ".*-tradelist-.*" -or
            $fileName -match "m\d+-tradelist-.*") {
        $tradelistFiles += $file
    }
}

# Display classification results
Write-Host "`nCANDLE FILES DETECTED:" -ForegroundColor Yellow
foreach ($file in $candleFiles) {
    Write-Host "  $file" -ForegroundColor Green
}

Write-Host "`nTRADELIST FILES DETECTED:" -ForegroundColor Yellow
foreach ($file in $tradelistFiles) {
    Write-Host "  $file" -ForegroundColor Green
}

# Ask for confirmation
Write-Host "`nDo you want to move files to their respective directories?" -ForegroundColor Cyan
Write-Host "  $($candleFiles.Count) candle files -> candles/" -ForegroundColor Green
Write-Host "  $($tradelistFiles.Count) tradelist files -> tradelist/" -ForegroundColor Green
$confirm = Read-Host "Enter [Y] to continue, [N] to cancel"

if ($confirm -match "^[Yy]$") {
    Write-Host "`nStarting file movement..." -ForegroundColor Green
    
    # Move candle files
    foreach ($file in $candleFiles) {
        $sourcePath = Join-Path $rootPath $file
        $destPath = Join-Path $candlesPath $file
        
        try {
            Move-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "  Moved: $file -> candles/" -ForegroundColor Green
        }
        catch {
            Write-Host "  Error moving $file : $_" -ForegroundColor Red
        }
    }
    
    # Move tradelist files
    foreach ($file in $tradelistFiles) {
        $sourcePath = Join-Path $rootPath $file
        $destPath = Join-Path $tradelistPath $file
        
        try {
            Move-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "  Moved: $file -> tradelist/" -ForegroundColor Green
        }
        catch {
            Write-Host "  Error moving $file : $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`nDATA ORGANIZATION COMPLETED!" -ForegroundColor Green
    Write-Host "New structure:" -ForegroundColor Cyan
    Write-Host "  candles/ - Contains $($candleFiles.Count) candle files" -ForegroundColor Yellow
    Write-Host "  tradelist/ - Contains $($tradelistFiles.Count) tradelist files" -ForegroundColor Yellow
    
} else {
    Write-Host "`nCancelled. Files remain in root directory." -ForegroundColor Yellow
}

Write-Host "`nScript completed!" -ForegroundColor Green