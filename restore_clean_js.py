#!/usr/bin/env python3
"""
Tạo lại JavaScript section clean cho strategy_management.html
"""

print("🔧 CREATING CLEAN JAVASCRIPT SECTION")

# Read current content up to JavaScript section
with open('templates/strategy_management.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find where JavaScript starts
js_start = content.find('    <!-- JavaScript -->')

if js_start == -1:
    print("❌ Could not find JavaScript section")
    exit(1)

# Keep everything before JavaScript
html_before_js = content[:js_start]

# Create clean JavaScript section
clean_js = '''    <!-- JavaScript -->
    <script>
        let selectedFile = null;
        let currentStrategyData = null;

        // File upload handling
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('strategyFile');
        const uploadForm = document.getElementById('uploadForm');
        const detectionPreview = document.getElementById('detectionPreview');
        const uploadResult = document.getElementById('uploadResult');

        if (uploadZone && fileInput) {
            // Drag and drop events
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0]);
                }
            });

            uploadZone.addEventListener('click', (e) => {
                if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                    return;
                }
                fileInput.click();
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFileSelect(e.target.files[0]);
                }
            });
        }

        if (uploadForm) {
            uploadForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (!selectedFile) {
                    showError('Please select a file first');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);
                
                const symbolOverride = document.getElementById('symbolOverride').value.trim();
                const strategyOverride = document.getElementById('strategyOverride').value.trim();
                
                if (symbolOverride) formData.append('symbol_override', symbolOverride);
                if (strategyOverride) formData.append('strategy_override', strategyOverride);

                try {
                    const response = await fetch('/api/strategies/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    
                    if (result.success) {
                        showSuccess(`Strategy uploaded successfully: ${result.filename}`);
                        await refreshStrategies();
                        
                        // Reset form
                        uploadForm.style.display = 'none';
                        detectionPreview.style.display = 'none';
                        uploadResult.innerHTML = '';
                        selectedFile = null;
                    } else {
                        showError(result.error || 'Upload failed');
                    }
                } catch (error) {
                    showError('Error uploading file: ' + error.message);
                }
            });
        }

        function handleFileSelect(file) {
            selectedFile = file;
            
            const reader = new FileReader();
            reader.onload = async (e) => {
                const content = e.target.result;
                
                try {
                    const detected = await detectStrategyInfo(file.name);
                    
                    document.getElementById('symbolOverride').value = detected.symbol || '';
                    document.getElementById('strategyOverride').value = detected.strategy || '';
                    
                    detectionPreview.innerHTML = `
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745;">
                            <h5 style="color: #155724; margin: 0 0 10px 0;">
                                <i class="fas fa-check-circle"></i> File Detection Results
                            </h5>
                            <p style="margin: 5px 0;"><strong>Filename:</strong> ${file.name}</p>
                            <p style="margin: 5px 0;"><strong>Detected Symbol:</strong> ${detected.symbol || 'Not detected'}</p>
                            <p style="margin: 5px 0;"><strong>Detected Strategy:</strong> ${detected.strategy || 'Not detected'}</p>
                            <p style="margin: 5px 0;"><strong>File Size:</strong> ${(file.size / 1024).toFixed(2)} KB</p>
                            <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
                                <i class="fas fa-info-circle"></i> 
                                Values have been auto-filled below. You can edit them before uploading.
                            </p>
                        </div>
                    `;
                    detectionPreview.style.display = 'block';
                    uploadForm.style.display = 'block';
                    
                } catch (error) {
                    showError('Error processing file: ' + error.message);
                }
            };
            reader.readAsText(file);
        }

        async function detectStrategyInfo(filename) {
            try {
                const response = await fetch('/api/strategies/detect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ filename: filename })
                });
                
                const result = await response.json();
                return result;
            } catch (error) {
                console.error('Detection error:', error);
                return { symbol: '', strategy: '' };
            }
        }

        function showError(message) {
            uploadResult.innerHTML = `<div style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px; border: 1px solid #f5c6cb;">${message}</div>`;
        }

        function showSuccess(message) {
            uploadResult.innerHTML = `<div style="color: #155724; background: #d4edda; padding: 10px; border-radius: 5px; border: 1px solid #c3e6cb;">${message}</div>`;
        }

        async function scanManualFiles() {
            try {
                const response = await fetch('/api/strategies/scan_manual', {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess(`Manual scan completed: ${result.imported_count} files imported`);
                    await refreshStrategies();
                } else {
                    showError(result.error || 'Manual scan failed');
                }
            } catch (error) {
                showError('Error scanning manual files: ' + error.message);
            }
        }

        async function refreshStrategies() {
            try {
                const response = await fetch('/api/strategies/list');
                const result = await response.json();
                
                if (result.success) {
                    updateStrategiesTable(result.strategies);
                }
            } catch (error) {
                console.error('Error refreshing strategies:', error);
            }
        }

        function updateStrategiesTable(strategies) {
            const tableBody = document.getElementById('strategiesTableBody');
            if (!tableBody) return;
            
            tableBody.innerHTML = strategies.map(strategy => `
                <tr data-symbol="${strategy.symbol}" data-strategy="${strategy.strategy_name}">
                    <td>
                        <strong>${strategy.strategy_name}</strong><br>
                        <small class="text-muted">${strategy.filename}</small>
                    </td>
                    <td>
                        <span class="badge symbol-badge">${strategy.symbol}</span>
                    </td>
                    <td>${strategy.timeframe}</td>
                    <td>
                        <span class="badge version-badge">${strategy.version}</span>
                    </td>
                    <td>${strategy.trade_count}</td>
                    <td>
                        <small>${strategy.date_range || 'N/A'}</small>
                    </td>
                    <td>
                        <small>${new Date(strategy.upload_date).toLocaleDateString()}</small>
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" title="Run backtest on Home page"
                                    onclick="runBacktest('${strategy.symbol}', '${strategy.timeframe}', '${strategy.strategy_name}', '${strategy.version}')">
                                <i class="fas fa-chart-line"></i> Test
                            </button>
                            <button class="btn btn-outline-info" title="View and edit strategy details"
                                    onclick="editStrategy('${strategy.symbol}', '${strategy.timeframe}', '${strategy.strategy_name}', '${strategy.version}')">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-outline-danger" title="Delete this strategy"
                                    onclick="deleteStrategy('${strategy.symbol}', '${strategy.timeframe}', '${strategy.strategy_name}', '${strategy.version}')">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }

        function runBacktest(symbol, timeframe, strategyName, version) {
            const params = new URLSearchParams({
                symbol: symbol,
                timeframe: timeframe,
                strategy: strategyName,
                version: version
            });
            window.open('/?auto_load=' + encodeURIComponent(params.toString()), '_blank');
        }

        async function editStrategy(symbol, timeframe, strategyName, version) {
            // Implement edit functionality
            alert('Edit functionality coming soon!');
        }

        async function deleteStrategy(symbol, timeframe, strategyName, version) {
            if (!confirm(`Are you sure you want to delete ${symbol} ${timeframe} ${strategyName} ${version}?`)) {
                return;
            }

            try {
                const response = await fetch('/api/strategies/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        symbol: symbol,
                        timeframe: timeframe,
                        strategy_name: strategyName,
                        version: version
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    await refreshStrategies();
                    alert('Strategy deleted successfully');
                } else {
                    alert('Error deleting strategy: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Error deleting strategy: ' + error.message);
            }
        }

        // Filter functionality
        function filterStrategies() {
            const symbolFilter = document.getElementById('symbolFilter');
            const strategyFilter = document.getElementById('strategyFilter');
            const searchInput = document.getElementById('searchInput');
            const tableBody = document.getElementById('strategiesTableBody');

            if (!symbolFilter || !tableBody) return;

            const symbolValue = symbolFilter.value.toLowerCase();
            const strategyValue = strategyFilter ? strategyFilter.value.toLowerCase() : '';
            const searchValue = searchInput ? searchInput.value.toLowerCase() : '';

            const rows = tableBody.querySelectorAll('tr');
            
            rows.forEach(row => {
                const symbol = (row.getAttribute('data-symbol') || '').toLowerCase();
                const strategy = (row.getAttribute('data-strategy') || '').toLowerCase();
                const text = row.textContent.toLowerCase();

                const symbolMatch = !symbolValue || symbol.includes(symbolValue);
                const strategyMatch = !strategyValue || strategy.includes(strategyValue);
                const searchMatch = !searchValue || text.includes(searchValue);

                if (symbolMatch && strategyMatch && searchMatch) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Add filter event listeners when page loads
        document.addEventListener('DOMContentLoaded', () => {
            const symbolFilter = document.getElementById('symbolFilter');
            const strategyFilter = document.getElementById('strategyFilter');
            const searchInput = document.getElementById('searchInput');

            if (symbolFilter) {
                symbolFilter.addEventListener('change', filterStrategies);
            }
            if (strategyFilter) {
                strategyFilter.addEventListener('change', filterStrategies);
            }
            if (searchInput) {
                searchInput.addEventListener('input', filterStrategies);
            }

            console.log('✅ Strategy Management initialized');
        });
    </script>
</body>
</html>'''

# Combine everything
new_content = html_before_js + clean_js

# Write back to file
with open('templates/strategy_management.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Clean JavaScript section created!")
print("📋 Restored functions:")
print("   - File upload & drag-drop")
print("   - Strategy management (Test, Edit, Delete)")
print("   - Filter functionality (Symbol, Strategy, Search)")
print("   - All event listeners properly configured")

print("🔄 Please refresh the Strategy Management page!")