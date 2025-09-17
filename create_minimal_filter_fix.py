#!/usr/bin/env python3
"""
Create a minimal filter fix that preserves all existing functionality
"""

print("🔧 CREATING MINIMAL FILTER FIX")

minimal_fix = '''
<!-- Add this BEFORE closing </body> tag -->
<script>
// MINIMAL filter fix - add after all existing JavaScript
(function() {
    'use strict';
    
    function addFilterFunctionality() {
        console.log('🔧 Adding minimal filter functionality...');
        
        const symbolFilter = document.getElementById('symbolFilter');
        const strategyFilter = document.getElementById('strategyFilter');
        const searchInput = document.getElementById('searchInput');
        const tableBody = document.getElementById('strategiesTableBody');
        
        if (!symbolFilter || !tableBody) {
            console.warn('⚠️ Filter elements not found, retrying...');
            setTimeout(addFilterFunctionality, 1000);
            return;
        }
        
        function performFilter() {
            const symbolValue = symbolFilter.value.toLowerCase();
            const strategyValue = strategyFilter ? strategyFilter.value.toLowerCase() : '';
            const searchValue = searchInput ? searchInput.value.toLowerCase() : '';
            
            console.log('🎯 Filtering:', {symbolValue, strategyValue, searchValue});
            
            const rows = tableBody.querySelectorAll('tr');
            let visible = 0;
            
            rows.forEach(row => {
                const symbol = (row.getAttribute('data-symbol') || '').toLowerCase();
                const strategy = (row.getAttribute('data-strategy') || '').toLowerCase();
                const text = row.textContent.toLowerCase();
                
                const symbolMatch = !symbolValue || symbol.includes(symbolValue);
                const strategyMatch = !strategyValue || strategy.includes(strategyValue);
                const searchMatch = !searchValue || text.includes(searchValue);
                
                if (symbolMatch && strategyMatch && searchMatch) {
                    row.style.display = '';
                    visible++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            console.log(`✅ Filter result: ${visible}/${rows.length} visible`);
        }
        
        // Add listeners
        symbolFilter.addEventListener('change', performFilter);
        if (strategyFilter) strategyFilter.addEventListener('change', performFilter);
        if (searchInput) searchInput.addEventListener('input', performFilter);
        
        console.log('✅ Filter functionality added successfully');
    }
    
    // Wait for page to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addFilterFunctionality);
    } else {
        addFilterFunctionality();
    }
})();
</script>
'''

with open('minimal_filter_fix.html', 'w', encoding='utf-8') as f:
    f.write(minimal_fix)

print("✅ Minimal filter fix created: minimal_filter_fix.html")
print("📋 Instructions:")
print("1. Copy the script content")
print("2. Add it RIGHT BEFORE </body> tag in strategy_management.html") 
print("3. This will add filter without touching existing functions")

print("🏁 Done!")