# ✅ SYSTEM HEALTH CHECKLIST

## 🔍 Pre-flight Check - Trước khi sử dụng

### 1. ⚙️ Environment Check
```bash
# Check Python version
python --version  # Should be 3.8+

# Check required packages
python -c "import flask, optuna, pandas, numpy; print('✅ All packages OK')"

# Check working directory
pwd  # Should be in BTC folder
```

### 2. 📊 Data Verification
```bash
# List available CSV files
ls *.csv | head -10

# Quick data check
python -c "
from data_manager import get_data_manager
dm = get_data_manager()
symbols = dm.get_available_symbols()
print(f'📊 Found {len(symbols)} symbols: {symbols}')
timeframes = dm.get_available_timeframes()
print(f'⏰ Timeframes: {timeframes}')
"
```

### 3. 🔧 System Components
```bash
# Test data manager
python -c "from data_manager import get_data_manager; print('✅ Data Manager OK')"

# Test results manager
python -c "from results_manager import get_results_manager; print('✅ Results Manager OK')"

# Test tradelist manager
python -c "from tradelist_manager import get_tradelist_manager; print('✅ Tradelist Manager OK')"

# Test web app import
python -c "import web_app; print('✅ Web App Import OK')"
```

---

## 🚀 Startup Checklist

### Web App Startup Sequence:
1. ✅ **Terminal Output Check**:
   ```
   📊 Discovered X symbols with data:
   ✅ CHẾ ĐỘ NÂNG CAO ĐÃ KÍCH HOẠT
   🚀 Starting Enhanced Trading Optimization Web App...
   🌐 Access at: http://localhost:5000
   * Running on http://127.0.0.1:5000
   * Debugger is active!
   ```

2. ✅ **Browser Access Check**:
   - http://localhost:5000 → Dashboard loads
   - Navigation menu visible
   - No 404 errors

3. ✅ **Route Accessibility**:
   - `/` → Home dashboard ✅
   - `/batch` → Batch processing page ✅
   - `/compare` → Compare results page ✅
   - `/analytics` → Analytics dashboard ✅

---

## 🧪 Functional Testing

### Test 1: Basic Optimization
```bash
# Via web interface:
1. Go to /batch
2. Select 1 symbol
3. Set trials: 10
4. Start optimization
5. Check progress updates
6. Verify results display

Expected: ✅ Completes in 2-5 minutes
```

### Test 2: Data Integration
```bash
# Check data pipeline:
1. Data files → Data Manager → Web interface
2. Optimization results → Results Manager → Display
3. Charts render correctly

Expected: ✅ All data flows correctly
```

### Test 3: API Endpoints
```bash
# Test key endpoints:
curl http://localhost:5000/api/analytics/history
curl http://localhost:5000/api/analytics/symbols

Expected: ✅ JSON responses
```

---

## 🔧 Performance Checklist

### Resource Usage:
```bash
# Check memory usage during batch
# Task Manager → python.exe process
# Should be < 2GB for normal batches

# Check CPU usage
# Should use configured number of workers
# 2-4 workers = 50-100% CPU utilization
```

### Optimization Performance:
```
✅ Single symbol, 50 trials: 2-5 minutes
✅ 3 symbols, 100 trials: 10-15 minutes  
✅ Progress updates every 2-3 seconds
✅ No memory leaks during long runs
```

---

## 🚨 Troubleshooting Checklist

### Common Issues Resolution:

#### Issue: ImportError
```bash
# Solution 1: Install missing packages
pip install flask optuna pandas numpy matplotlib

# Solution 2: Check Python path
python -c "import sys; print(sys.path)"

# Solution 3: Reinstall requirements
pip install -r requirements.txt
```

#### Issue: No symbols found
```bash
# Check 1: File naming convention
ls BINANCE_*.csv    # Should show trading data files
ls *tradelist*.csv  # Should show tradelist files

# Check 2: File content
head -5 BINANCE_BTCUSDT.P,\ 30.csv

# Solution: Verify file format matches expected schema
```

#### Issue: 404 errors on routes
```bash
# Solution 1: Restart web app
Ctrl+C
python web_app.py

# Solution 2: Check templates folder
ls templates/

# Solution 3: Clear browser cache
Ctrl+Shift+R
```

#### Issue: Batch processing stuck
```bash
# Check 1: Terminal output for errors
# Look for exception traces

# Check 2: Reduce complexity
# Lower trials count, fewer symbols

# Check 3: Resource constraints
# Close other applications
# Check available RAM/CPU
```

#### Issue: Charts not loading
```bash
# Check 1: Internet connection
# Chart.js loads from CDN

# Check 2: Browser console
# F12 → Console tab → Look for errors

# Check 3: Try different browser
# Chrome, Firefox, Edge
```

---

## 📊 Health Monitoring

### During Operation - Monitor These:

#### Terminal Output:
```
✅ No ERROR messages
✅ Progress updates flowing
✅ No memory warnings
✅ Optimization completing normally
```

#### Browser Console (F12):
```
✅ No JavaScript errors
✅ AJAX requests succeeding  
✅ Charts rendering correctly
✅ No 404/500 errors
```

#### System Resources:
```
✅ Memory usage stable
✅ CPU usage appropriate for worker count
✅ Disk space sufficient for results
✅ No excessive file handles
```

---

## 🔄 Maintenance Checklist

### Daily (if using heavily):
- [ ] Check log files for errors
- [ ] Monitor result database size
- [ ] Clear old batch status data

### Weekly:
- [ ] Backup optimization results
- [ ] Update data files if needed
- [ ] Check for system updates

### Monthly:
- [ ] Archive old results
- [ ] Performance optimization review
- [ ] Security updates

---

## 🎯 Success Criteria

### System is healthy when:
✅ Web app starts without errors
✅ All routes accessible (/, /batch, /compare, /analytics)
✅ Can complete 50-trial optimization in <5 minutes
✅ Charts and visualizations render correctly
✅ Can export results and data
✅ Memory usage stable during long operations
✅ No data corruption or loss

### Ready for production when:
✅ Passes all functional tests
✅ Performance meets requirements
✅ Error handling works correctly
✅ Data backup system in place
✅ Monitoring and alerting configured

---

## 📞 Emergency Procedures

### If system completely broken:
1. **Stop all processes**: Ctrl+C in all terminals
2. **Backup current state**: Copy entire BTC folder
3. **Restart clean**: 
   ```bash
   cd BTC
   python web_app.py
   ```
4. **Verify basic functionality**: Test single optimization
5. **Escalate if needed**: Check troubleshooting guides

### Data recovery:
- Results stored in: `slbe_ts_opt_results.csv`
- Backup files: `BACKUP_*` folders
- Logs: Terminal output and browser console

**🚀 System is GO when all checks pass! 🎉**