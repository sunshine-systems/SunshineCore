#!/bin/bash

echo "=========================================="
echo "SocketIO UI Connection Fix"
echo "=========================================="

cd sunshine/sunshine_systems

echo "Fixing Control Panel UI SocketIO connection..."

# Fix the HTML template with better SocketIO loading and error handling
cat > templates/control_panel/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunshine Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #fff;
            height: 100vh;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 300;
        }
        
        .connection-status {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .connected {
            background: #28a745;
            color: white;
        }
        
        .disconnected {
            background: #dc3545;
            color: white;
        }
        
        .loading {
            background: #ffc107;
            color: #212529;
        }
        
        .main-container {
            display: flex;
            height: calc(100vh - 80px);
        }
        
        .sidebar {
            width: 300px;
            background: #2d2d2d;
            border-right: 1px solid #444;
            overflow-y: auto;
        }
        
        .content {
            flex: 1;
            background: #1e1e1e;
            overflow-y: auto;
        }
        
        .section {
            margin: 1rem;
            background: #333;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .section-header {
            background: #404040;
            padding: 0.8rem 1rem;
            font-weight: 600;
            border-bottom: 1px solid #555;
        }
        
        .section-content {
            padding: 1rem;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .process-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            margin: 0.3rem 0;
            background: #444;
            border-radius: 4px;
            border-left: 4px solid #28a745;
        }
        
        .process-item.dead {
            border-left-color: #dc3545;
            opacity: 0.7;
        }
        
        .process-name {
            font-weight: 600;
        }
        
        .process-pid {
            font-size: 0.9rem;
            color: #aaa;
        }
        
        .process-status {
            padding: 0.2rem 0.5rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .status-active {
            background: #28a745;
            color: white;
        }
        
        .status-dead {
            background: #dc3545;
            color: white;
        }
        
        .message-item {
            padding: 0.5rem;
            margin: 0.3rem 0;
            background: #2a2a2a;
            border-radius: 4px;
            border-left: 3px solid #667eea;
            font-size: 0.9rem;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.3rem;
            font-size: 0.8rem;
            color: #aaa;
        }
        
        .message-type {
            color: #667eea;
            font-weight: 600;
        }
        
        .message-content {
            color: #ddd;
        }
        
        .controls {
            padding: 1rem;
            background: #333;
            border-top: 1px solid #444;
        }
        
        .control-group {
            margin-bottom: 1rem;
        }
        
        .control-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #ccc;
        }
        
        .control-input {
            width: 100%;
            padding: 0.5rem;
            background: #2a2a2a;
            border: 1px solid #555;
            border-radius: 4px;
            color: #fff;
        }
        
        .control-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.7rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .control-button:hover {
            transform: translateY(-1px);
        }
        
        .danger-button {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }
        
        .stats {
            display: flex;
            justify-content: space-around;
            padding: 1rem;
            background: #333;
            margin: 1rem;
            border-radius: 8px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #aaa;
        }
        
        .debug-info {
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            padding: 10px;
            border-radius: 5px;
            font-size: 0.8rem;
            color: #ccc;
            max-width: 300px;
            max-height: 150px;
            overflow-y: auto;
        }
        
        .error-message {
            background: #dc3545;
            color: white;
            padding: 10px;
            margin: 10px;
            border-radius: 5px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Sunshine Control Panel</h1>
        <div id="connection-status" class="connection-status loading">Loading...</div>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div class="section">
                <div class="section-header">System Statistics</div>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="process-count">0</div>
                        <div class="stat-label">Processes</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="message-count">0</div>
                        <div class="stat-label">Messages</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">Active Processes</div>
                <div class="section-content" id="processes-list">
                    <div style="text-align: center; color: #666; padding: 2rem;">
                        Loading processes...
                    </div>
                </div>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label for="shutdown-target">Shutdown Target:</label>
                    <input type="text" id="shutdown-target" class="control-input" placeholder="Process name or * for all">
                </div>
                <button class="control-button danger-button" onclick="shutdownProcess()">Shutdown Process</button>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-header">System Messages</div>
                <div class="section-content" id="messages-list" style="max-height: calc(100vh - 200px);">
                    <div style="text-align: center; color: #666; padding: 2rem;">
                        Loading messages...
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="debug-info" class="debug-info">
        <div>Initializing Control Panel...</div>
    </div>

    <!-- Multiple CDN fallbacks for SocketIO -->
    <script>
        // Try to load Socket.IO from multiple CDNs with fallbacks
        function loadSocketIO() {
            const scripts = [
                'https://cdn.socket.io/4.7.4/socket.io.min.js',
                'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.js',
                'https://unpkg.com/socket.io-client@4.7.4/dist/socket.io.js'
            ];
            
            let currentIndex = 0;
            
            function tryLoadScript() {
                if (currentIndex >= scripts.length) {
                    debugLog('❌ Failed to load Socket.IO from all CDNs');
                    showError('Failed to load Socket.IO library. Please check your internet connection.');
                    return;
                }
                
                const script = document.createElement('script');
                script.src = scripts[currentIndex];
                script.onload = function() {
                    debugLog(`✅ Socket.IO loaded from: ${scripts[currentIndex]}`);
                    initializeSocketIO();
                };
                script.onerror = function() {
                    debugLog(`❌ Failed to load from: ${scripts[currentIndex]}`);
                    currentIndex++;
                    tryLoadScript();
                };
                document.head.appendChild(script);
            }
            
            tryLoadScript();
        }
        
        // Initialize Socket.IO connection
        function initializeSocketIO() {
            if (typeof io === 'undefined') {
                debugLog('❌ Socket.IO not available after loading');
                showError('Socket.IO library loaded but not available');
                return;
            }
            
            debugLog('🔄 Initializing Socket.IO connection...');
            
            const socket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                timeout: 5000
            });
            
            setupSocketEvents(socket);
        }
        
        // Setup all socket event handlers
        function setupSocketEvents(socket) {
            let processes = [];
            let messages = [];
            
            // Connection events
            socket.on('connect', function() {
                debugLog('✅ Connected to Control Panel SocketIO');
                updateConnectionStatus(true);
            });
            
            socket.on('disconnect', function() {
                debugLog('❌ Disconnected from Control Panel SocketIO');
                updateConnectionStatus(false);
            });
            
            socket.on('connect_error', function(error) {
                debugLog(`❌ Connection error: ${error.message}`);
                updateConnectionStatus(false);
            });
            
            // Data events
            socket.on('processes_update', function(data) {
                debugLog(`📊 Received processes_update with ${data.length} processes`);
                processes = data;
                updateProcessesList(processes);
                updateStats(processes.length, messages.length);
            });
            
            socket.on('message_received', function(message) {
                debugLog(`📨 Received message: ${message.message_type} from ${message.sender}`);
                messages.unshift(message);
                if (messages.length > 100) {
                    messages = messages.slice(0, 100);
                }
                updateMessagesList(messages);
                updateStats(processes.length, messages.length);
            });
            
            socket.on('messages_update', function(data) {
                debugLog(`📨 Received messages_update with ${data.length} messages`);
                messages = data.reverse();
                updateMessagesList(messages);
                updateStats(processes.length, messages.length);
            });
            
            // Store socket reference globally for other functions
            window.controlPanelSocket = socket;
        }
        
        // Debug logging
        function debugLog(message) {
            const timestamp = new Date().toLocaleTimeString();
            const logMessage = `[${timestamp}] ${message}`;
            console.log(logMessage);
            
            const debugDiv = document.getElementById('debug-info');
            debugDiv.innerHTML = logMessage + '<br>' + debugDiv.innerHTML;
            
            // Keep only last 15 debug messages
            const lines = debugDiv.innerHTML.split('<br>');
            if (lines.length > 15) {
                debugDiv.innerHTML = lines.slice(0, 15).join('<br>');
            }
        }
        
        // Show error message
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = message;
            document.body.insertBefore(errorDiv, document.body.firstChild);
            updateConnectionStatus(false);
        }
        
        // Connection status
        function updateConnectionStatus(connected) {
            const statusDiv = document.getElementById('connection-status');
            if (connected) {
                statusDiv.textContent = 'Connected';
                statusDiv.className = 'connection-status connected';
            } else {
                statusDiv.textContent = 'Disconnected';  
                statusDiv.className = 'connection-status disconnected';
            }
        }
        
        // UI Update functions
        function updateProcessesList(processes) {
            const container = document.getElementById('processes-list');
            
            if (processes.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">No processes registered</div>';
                return;
            }
            
            container.innerHTML = processes.map(process => `
                <div class="process-item ${process.status === 'dead' ? 'dead' : ''}">
                    <div>
                        <div class="process-name">${process.name}</div>
                        <div class="process-pid">PID: ${process.pid}</div>
                    </div>
                    <div class="process-status status-${process.status}">${process.status.toUpperCase()}</div>
                </div>
            `).join('');
        }
        
        function updateMessagesList(messages) {
            const container = document.getElementById('messages-list');
            
            if (messages.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Waiting for messages...</div>';
                return;
            }
            
            container.innerHTML = messages.map(message => {
                const timestamp = new Date(message.datetime).toLocaleTimeString();
                const payload = JSON.stringify(message.payload, null, 2);
                
                return `
                    <div class="message-item">
                        <div class="message-header">
                            <span class="message-type">${message.message_type}</span>
                            <span>${message.sender} - ${timestamp}</span>
                        </div>
                        <div class="message-content">
                            <pre>${payload}</pre>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats(processCount, messageCount) {
            document.getElementById('process-count').textContent = processCount;
            document.getElementById('message-count').textContent = messageCount;
        }
        
        function shutdownProcess() {
            const target = document.getElementById('shutdown-target').value.trim();
            if (!target) {
                alert('Please enter a process name or * for all processes');
                return;
            }
            
            if (confirm(`Are you sure you want to shutdown "${target}"?`)) {
                // This would normally send a message through the backend
                // For now, we'll just show an alert
                alert(`Shutdown command would be sent to: ${target}`);
                document.getElementById('shutdown-target').value = '';
            }
        }
        
        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {
            debugLog('🚀 Control Panel UI initializing...');
            updateConnectionStatus(false);
            loadSocketIO();
        });
    </script>
</body>
</html>
EOF

echo ""
echo "=========================================="
echo "SocketIO UI Fix Applied!"
echo "=========================================="
echo ""
echo "Fixed issues:"
echo "✅ Multiple CDN fallbacks for Socket.IO library loading"
echo "✅ Proper loading sequence with error handling"
echo "✅ Enhanced connection status tracking" 
echo "✅ Better error messages and debugging"
echo "✅ Improved initialization flow"
echo "✅ Robust fallback mechanisms"
echo ""
echo "The Control Panel UI should now:"
echo "- Load Socket.IO from multiple CDN sources"
echo "- Show proper connection status"
echo "- Display all registered processes"
echo "- Show real-time messages from both processes"
echo "- Provide detailed debug information"
echo ""
echo "Refresh your browser at http://127.0.0.1:2828"
echo "You should see 'Connected' status and both processes listed!"