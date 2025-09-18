// Enhanced Error Detection Script
(function() {
    'use strict';
    
    // Store original console methods
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;
    
    // Create error display div
    function createErrorDisplay() {
        const errorDiv = document.createElement('div');
        errorDiv.id = 'js-error-display';
        errorDiv.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 400px;
            max-height: 300px;
            overflow-y: auto;
            background: #ff0000;
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 10000;
            font-family: monospace;
            font-size: 12px;
            display: none;
        `;
        document.body.appendChild(errorDiv);
        return errorDiv;
    }
    
    let errorDisplay = null;
    
    function showError(message, source = '', line = '', col = '') {
        if (!errorDisplay) {
            errorDisplay = createErrorDisplay();
        }
        
        errorDisplay.style.display = 'block';
        const timestamp = new Date().toLocaleTimeString();
        errorDisplay.innerHTML += `
            <div style="border-bottom: 1px solid #fff; margin-bottom: 5px; padding-bottom: 5px;">
                <strong>[${timestamp}]</strong><br>
                <strong>Error:</strong> ${message}<br>
                ${source ? `<strong>Source:</strong> ${source}<br>` : ''}
                ${line ? `<strong>Line:</strong> ${line}${col ? `, Col: ${col}` : ''}<br>` : ''}
            </div>
        `;
        errorDisplay.scrollTop = errorDisplay.scrollHeight;
    }
    
    // Override console.error
    console.error = function(...args) {
        showError(args.join(' '));
        originalError.apply(console, args);
    };
    
    // Global error handler
    window.onerror = function(message, source, lineno, colno, error) {
        showError(message, source, lineno, colno);
        return false; // Don't prevent default behavior
    };
    
    // Promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        showError('Unhandled Promise Rejection: ' + event.reason);
    });
    
    // Log that the error detector is active
    console.log('🔍 JavaScript Error Detector Active');
})();