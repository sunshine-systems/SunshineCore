#!/bin/bash

echo "=========================================="
echo "Simplify Message Details to Raw JSON"
echo "=========================================="

cd sunshine/sunshine_systems

echo "Updating UI to show raw message data..."

# Update just the selectMessage function in the HTML
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
        
        :root {
            --bg: #0a0a0a;
            --panel-bg: #111111;
            --border: rgba(255, 255, 255, 0.08);
            --text: #ffffff;
            --text-dim: #666666;
            --accent: #667eea;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #3b82f6;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
            font-size: 14px;
        }
        
        .container {
            display: flex;
            height: 100vh;
        }
        
        /* Left Panel - System Overview */
        .left-panel {
            width: 280px;
            background: var(--panel-bg);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 1.5rem;
            gap: 1.5rem;
        }
        
        .logo {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 0.5rem;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-dim);
        }
        
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--danger);
        }
        
        .status-dot.connected {
            background: var(--success);
        }
        
        .stats {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
        }
        
        .stat-label {
            color: var(--text-dim);
            font-size: 0.875rem;
        }
        
        .stat-value {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent);
        }
        
        .processes {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            overflow-y: auto;
        }
        
        .process {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .process:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .process-name {
            font-weight: 500;
        }
        
        .process-status {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--success);
        }
        
        .shutdown-section {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .shutdown-input {
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 0.875rem;
        }
        
        .shutdown-btn {
            padding: 0.5rem;
            background: var(--danger);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        
        .shutdown-btn:hover {
            opacity: 0.8;
        }
        
        /* Middle Panel - Messages */
        .middle-panel {
            flex: 1;
            background: var(--bg);
            display: flex;
            flex-direction: column;
        }
        
        .message-filters {
            display: flex;
            gap: 0.5rem;
            padding: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .filter {
            padding: 0.25rem 0.75rem;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text-dim);
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .filter:hover {
            color: var(--text);
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        .filter.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 0.5rem;
        }
        
        .message {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem;
            margin-bottom: 0.25rem;
            background: var(--panel-bg);
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.875rem;
        }
        
        .message:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .message.selected {
            background: rgba(102, 126, 234, 0.15);
            border-left: 2px solid var(--accent);
        }
        
        .message-type {
            padding: 0.125rem 0.5rem;
            border-radius: 3px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            min-width: 60px;
            text-align: center;
        }
        
        .type-PING, .type-PONG {
            background: rgba(59, 130, 246, 0.15);
            color: var(--info);
        }
        
        .type-REGISTER, .type-REGISTER_ACK {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }
        
        .type-LOG {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-dim);
        }
        
        .type-SHUTDOWN {
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }
        
        .message-sender {
            flex: 1;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .message-preview {
            flex: 2;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 0.8rem;
        }
        
        .message-time {
            color: var(--text-dim);
            font-size: 0.75rem;
        }
        
        /* Right Panel - Message Details */
        .right-panel {
            width: 400px;
            background: var(--panel-bg);
            border-left: 1px solid var(--border);
            padding: 1rem;
            overflow-y: auto;
        }
        
        .raw-json {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.875rem;
            color: var(--text);
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.5;
        }
        
        .empty-state {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-dim);
            font-size: 0.875rem;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Panel - System Overview -->
        <div class="left-panel">
            <div>
                <div class="logo">🌟 Sunshine Control Panel</div>
                <div class="connection-status">
                    <div id="status-dot" class="status-dot"></div>
                    <span id="status-text">Disconnected</span>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <span class="stat-label">Active Processes</span>
                    <span class="stat-value" id="process-count">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Messages/Min</span>
                    <span class="stat-value" id="message-rate">0</span>
                </div>
            </div>
            
            <div class="processes" id="processes-list">
                <!-- Processes will be added here -->
            </div>
            
            <div class="shutdown-section">
                <input type="text" id="shutdown-target" class="shutdown-input" placeholder="Process name or * for all">
                <button class="shutdown-btn" onclick="shutdownProcess()">Shutdown Process</button>
            </div>
        </div>
        
        <!-- Middle Panel - Messages -->
        <div class="middle-panel">
            <div class="message-filters">
                <button class="filter active" data-filter="all">All</button>
                <button class="filter" data-filter="PING,PONG">Heartbeat</button>
                <button class="filter" data-filter="REGISTER,REGISTER_ACK">Registration</button>
                <button class="filter" data-filter="LOG">Logs</button>
                <button class="filter" data-filter="other">Other</button>
            </div>
            <div class="messages" id="messages-list">
                <!-- Messages will be added here -->
            </div>
        </div>
        
        <!-- Right Panel - Message Details -->
        <div class="right-panel" id="detail-content">
            <div class="empty-state">
                Select a message to view details
            </div>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
    <script>
        let socket = null;
        let processes = [];
        let messages = [];
        let selectedMessage = null;
        let activeFilter = 'all';
        let messageCount = 0;
        let messageCountStart = Date.now();
        
        // Initialize Socket.IO
        function initializeSocket() {
            socket = io();
            
            socket.on('connect', () => {
                document.getElementById('status-dot').classList.add('connected');
                document.getElementById('status-text').textContent = 'Connected';
            });
            
            socket.on('disconnect', () => {
                document.getElementById('status-dot').classList.remove('connected');
                document.getElementById('status-text').textContent = 'Disconnected';
            });
            
            socket.on('processes_update', (data) => {
                processes = data;
                updateProcesses();
            });
            
            socket.on('message_received', (message) => {
                messages.unshift(message);
                messageCount++;
                if (messages.length > 1000) {
                    messages = messages.slice(0, 1000);
                }
                updateMessages();
                updateMessageRate();
            });
            
            socket.on('messages_update', (data) => {
                messages = data.reverse();
                updateMessages();
            });
        }
        
        // Update processes
        function updateProcesses() {
            const container = document.getElementById('processes-list');
            const activeCount = processes.filter(p => p.status === 'active').length;
            
            document.getElementById('process-count').textContent = activeCount;
            
            container.innerHTML = processes.map(process => `
                <div class="process">
                    <span class="process-name">${process.name}</span>
                    <div class="process-status ${process.status !== 'active' ? 'dead' : ''}"></div>
                </div>
            `).join('');
        }
        
        // Update messages
        function updateMessages() {
            const container = document.getElementById('messages-list');
            
            let filtered = messages;
            if (activeFilter !== 'all') {
                if (activeFilter === 'other') {
                    const exclude = ['PING', 'PONG', 'REGISTER', 'REGISTER_ACK', 'LOG'];
                    filtered = messages.filter(m => !exclude.includes(m.message_type));
                } else {
                    const types = activeFilter.split(',');
                    filtered = messages.filter(m => types.includes(m.message_type));
                }
            }
            
            container.innerHTML = filtered.slice(0, 200).map((msg, idx) => {
                const time = new Date(msg.datetime).toLocaleTimeString();
                let preview = '';
                
                if (msg.payload) {
                    if (msg.message_type === 'LOG') {
                        preview = msg.payload.message || '';
                    } else if (msg.message_type === 'PING') {
                        preview = `Ping #${msg.payload.ping_number || ''}`;
                    } else if (msg.payload.process_name) {
                        preview = `Process: ${msg.payload.process_name}`;
                    } else {
                        preview = Object.keys(msg.payload).join(', ');
                    }
                }
                
                return `
                    <div class="message ${selectedMessage === msg ? 'selected' : ''}" 
                         onclick="selectMessage(${filtered.indexOf(msg)})">
                        <span class="message-type type-${msg.message_type}">${msg.message_type}</span>
                        <span class="message-sender">${msg.sender}</span>
                        <span class="message-preview">${preview}</span>
                        <span class="message-time">${time}</span>
                    </div>
                `;
            }).join('');
        }
        
        // Select message - SIMPLIFIED TO SHOW RAW JSON
        function selectMessage(index) {
            let filtered = messages;
            if (activeFilter !== 'all') {
                if (activeFilter === 'other') {
                    const exclude = ['PING', 'PONG', 'REGISTER', 'REGISTER_ACK', 'LOG'];
                    filtered = messages.filter(m => !exclude.includes(m.message_type));
                } else {
                    const types = activeFilter.split(',');
                    filtered = messages.filter(m => types.includes(m.message_type));
                }
            }
            
            selectedMessage = filtered[index];
            updateMessages();
            
            const detail = document.getElementById('detail-content');
            if (selectedMessage) {
                // Just show the raw JSON data
                detail.innerHTML = `<pre class="raw-json">${JSON.stringify(selectedMessage, null, 2)}</pre>`;
            }
        }
        
        // Update message rate
        function updateMessageRate() {
            const elapsed = (Date.now() - messageCountStart) / 1000 / 60;
            const rate = Math.round(messageCount / elapsed);
            document.getElementById('message-rate').textContent = rate;
        }
        
        // Filter handling
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter')) {
                document.querySelectorAll('.filter').forEach(f => f.classList.remove('active'));
                e.target.classList.add('active');
                activeFilter = e.target.dataset.filter;
                updateMessages();
            }
        });
        
        // Shutdown process
        function shutdownProcess() {
            const target = document.getElementById('shutdown-target').value.trim();
            if (!target) {
                alert('Please enter a process name or * for all');
                return;
            }
            
            if (confirm(`Shutdown "${target}"?`)) {
                socket.emit('send_shutdown', { target });
                document.getElementById('shutdown-target').value = '';
            }
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initializeSocket();
            setInterval(updateMessageRate, 5000);
        });
    </script>
</body>
</html>
EOF

echo ""
echo "=========================================="
echo "Raw JSON Message Details Applied!"
echo "=========================================="
echo ""
echo "Changes made:"
echo "✅ Right panel now shows raw JSON data"
echo "✅ No formatting - just the complete message object"
echo "✅ Easier to see all message properties at once"
echo "✅ Clean monospace font for JSON display"
echo ""
echo "Refresh http://127.0.0.1:2828 to see the simplified view!"