#!/usr/bin/env python3
"""
Tạo một JavaScript fix đơn giản chỉ để fix filter functionality
"""

print("🔧 CREATING SIMPLE FILTER FIX")

fix_js = '''
<script>
// Simple filter fix - override any existing issues
window.addEventListener('load', function() {
    console.log('🔧 Loading simple filter fix...');
    
    // Wait a bit more to ensure everything is loaded
    setTimeout(function() {
        console.log('🔧 Applying filter fix...');
        
        // Find elements with error handling
        const symbolFilter = document.getElementById('symbolFilter');
        const strategyFilter = document.getElementById('strategyFilter');
        const searchInput = document.getElementById('searchInput');
        const tableBody = document.getElementById('strategiesTableBody');
        
        console.log('🔧 Elements found:', {
            symbolFilter: !!symbolFilter,
            strategyFilter: !!strategyFilter,
            searchInput: !!searchInput,
            tableBody: !!tableBody
        });
        
        if (!symbolFilter || !tableBody) {
            console.error('❌ Required elements not found');
            return;
        }
        
        // Clear any existing listeners and add new ones
        const newSymbolFilter = symbolFilter.cloneNode(true);
        symbolFilter.parentNode.replaceChild(newSymbolFilter, symbolFilter);
        
        // Simple filter function
        function simpleFilter() {
            const selectedSymbol = newSymbolFilter.value.toLowerCase();
            console.log('🎯 Filtering by symbol:', selectedSymbol);
            
            const rows = tableBody.querySelectorAll('tr');
            let visibleCount = 0;
            
            rows.forEach((row, index) => {
                const symbol = row.getAttribute('data-symbol');
                
                if (!symbol) {
                    console.warn(`⚠️ Row ${index} has no data-symbol`);
                    return;
                }
                
                const shouldShow = !selectedSymbol || symbol.toLowerCase().includes(selectedSymbol);
                
                if (shouldShow) {
                    row.style.display = '';
                    row.style.backgroundColor = '#d4edda'; // Light green
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                    row.style.backgroundColor = '#f8d7da'; // Light red
                }
                
                console.log(`Row ${index}: ${symbol} → ${shouldShow ? 'SHOW' : 'HIDE'}`);
            });
            
            console.log(`✅ Filter complete: ${visibleCount}/${rows.length} rows visible`);
        }
        
        // Add event listener
        newSymbolFilter.addEventListener('change', simpleFilter);
        console.log('✅ Simple filter fix applied successfully');
        
        // Test filter
        setTimeout(() => {
            console.log('🧪 Testing filter with SAGAUSDT...');
            newSymbolFilter.value = 'SAGAUSDT';
            simpleFilter();
            
            setTimeout(() => {
                console.log('🔄 Resetting filter...');
                newSymbolFilter.value = '';
                simpleFilter();
            }, 3000);
        }, 1000);
        
    }, 2000);
});
</script>
'''

# Save to file
with open('filter_fix.html', 'w', encoding='utf-8') as f:
    f.write(fix_js)

print("✅ Filter fix created: filter_fix.html")
print("📋 To apply:")
print("1. Copy the script content")
print("2. Paste it at the end of strategy_management.html before </body>")
print("3. Or inject it via browser console")

print("🏁 Done!")