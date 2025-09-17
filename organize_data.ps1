# ============================================================================
# 📁 SCRIPT TỰ ĐỘNG TỔ CHỨC DỮ LIỆU TRADING
# ============================================================================

Write-Host "🚀 Bắt đầu tổ chức dữ liệu trading..." -ForegroundColor Green

# Đường dẫn thư mục
$rootPath = Get-Location
$candlesPath = Join-Path $rootPath "candles"
$tradelistPath = Join-Path $rootPath "tradelist"

Write-Host "📁 Thư mục gốc: $rootPath" -ForegroundColor Cyan
Write-Host "📈 Thư mục nến: $candlesPath" -ForegroundColor Yellow
Write-Host "📊 Thư mục tradelist: $tradelistPath" -ForegroundColor Yellow

# Tạo thư mục nếu chưa có
if (-not (Test-Path $candlesPath)) {
    New-Item -ItemType Directory -Path $candlesPath -Force
    Write-Host "✅ Đã tạo thư mục candles" -ForegroundColor Green
}

if (-not (Test-Path $tradelistPath)) {
    New-Item -ItemType Directory -Path $tradelistPath -Force
    Write-Host "✅ Đã tạo thư mục tradelist" -ForegroundColor Green
}

Write-Host "`n🔍 Scanning file CSV..." -ForegroundColor Cyan

# Lấy danh sách tất cả file CSV trong thư mục gốc
$csvFiles = Get-ChildItem -Path $rootPath -Name "*.csv" | Where-Object { 
    $_ -notlike "*\*" -and (Test-Path (Join-Path $rootPath $_)) 
}

$candleFiles = @()
$tradelistFiles = @()
$unknownFiles = @()

# Phân loại file
foreach ($file in $csvFiles) {
    $fileName = $file.ToLower()
    
    # Kiểm tra file candle (dữ liệu nến)
    if ($fileName -match "binance.*\.(csv)$" -and 
        ($fileName -match "\d+\.csv$" -or $fileName -match ", \d+\.csv$")) {
        $candleFiles += $file
    }
    # Kiểm tra file tradelist
    elseif ($fileName -match "tradelist" -or 
            $fileName -match "trade.*list" -or
            $fileName -match ".*-tradelist-.*" -or
            $fileName -match "m\d+-tradelist-.*") {
        $tradelistFiles += $file
    }
    else {
        $unknownFiles += $file
    }
}

# Hiển thị kết quả phân loại
Write-Host "`n📈 FILE CANDLE PHÁT HIỆN:" -ForegroundColor Yellow
foreach ($file in $candleFiles) {
    Write-Host "  ✅ $file" -ForegroundColor Green
}

Write-Host "`n📊 FILE TRADELIST PHÁT HIỆN:" -ForegroundColor Yellow
foreach ($file in $tradelistFiles) {
    Write-Host "  ✅ $file" -ForegroundColor Green
}

if ($unknownFiles.Count -gt 0) {
    Write-Host "`n❓ FILE KHÔNG XÁC ĐỊNH:" -ForegroundColor Magenta
    foreach ($file in $unknownFiles) {
        Write-Host "  ⚠️ $file" -ForegroundColor Yellow
    }
}

# Hỏi xác nhận trước khi di chuyển
Write-Host "`n🤔 Bạn có muốn di chuyển file vào thư mục tương ứng không?" -ForegroundColor Cyan
Write-Host "   📈 $($candleFiles.Count) file candle -> candles/" -ForegroundColor Green
Write-Host "   📊 $($tradelistFiles.Count) file tradelist -> tradelist/" -ForegroundColor Green
$confirm = Read-Host "Nhập [Y/y] để tiếp tục, [N/n] để hủy"

if ($confirm -match "^[Yy]$") {
    Write-Host "`n🔄 Bắt đầu di chuyển file..." -ForegroundColor Green
    
    # Di chuyển file candle
    foreach ($file in $candleFiles) {
        $sourcePath = Join-Path $rootPath $file
        $destPath = Join-Path $candlesPath $file
        
        try {
            Move-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "  ✅ Moved: $file -> candles/" -ForegroundColor Green
        }
        catch {
            Write-Host "  ❌ Error moving $file : $_" -ForegroundColor Red
        }
    }
    
    # Di chuyển file tradelist
    foreach ($file in $tradelistFiles) {
        $sourcePath = Join-Path $rootPath $file
        $destPath = Join-Path $tradelistPath $file
        
        try {
            Move-Item -Path $sourcePath -Destination $destPath -Force
            Write-Host "  ✅ Moved: $file -> tradelist/" -ForegroundColor Green
        }
        catch {
            Write-Host "  ❌ Error moving $file : $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`n🎉 HOÀN THÀNH TỔ CHỨC DỮ LIỆU!" -ForegroundColor Green
    Write-Host "📁 Cấu trúc mới:" -ForegroundColor Cyan
    Write-Host "   📈 candles/ - Chứa $($candleFiles.Count) file dữ liệu nến" -ForegroundColor Yellow
    Write-Host "   📊 tradelist/ - Chứa $($tradelistFiles.Count) file tradelist" -ForegroundColor Yellow
    
    # Hiển thị file trong mỗi thư mục
    Write-Host "`n📈 File trong candles/:" -ForegroundColor Yellow
    $candleContent = Get-ChildItem -Path $candlesPath -Name "*.csv" 2>$null
    if ($candleContent) {
        foreach ($file in $candleContent) {
            Write-Host "   📊 $file" -ForegroundColor Green
        }
    } else {
        Write-Host "   (Trống)" -ForegroundColor Gray
    }
    
    Write-Host "`n📊 File trong tradelist/:" -ForegroundColor Yellow
    $tradelistContent = Get-ChildItem -Path $tradelistPath -Name "*.csv" 2>$null
    if ($tradelistContent) {
        foreach ($file in $tradelistContent) {
            Write-Host "   📈 $file" -ForegroundColor Green
        }
    } else {
        Write-Host "   (Trống)" -ForegroundColor Gray
    }
    
} else {
    Write-Host "`n⏹️ Đã hủy. File vẫn ở thư mục gốc." -ForegroundColor Yellow
}

Write-Host "`n✨ Script hoàn thành!" -ForegroundColor Green