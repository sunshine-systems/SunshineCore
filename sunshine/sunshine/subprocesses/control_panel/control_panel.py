#!/usr/bin/env python3
import os
import sys

# Set terminal title
if sys.platform == "win32":
    os.system("title Sunshine - Control Panel")
"""Control Panel with Web UI - Handles registration, heartbeats, and shows all messages"""
import os
import sys
import time
import json
import threading
import webbrowser
from datetime import datetime, timezone
from collections import deque
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from utils.zeromq_utils import MessageBus
from utils import topics

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sunshine-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sunshine Control Panel</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .status-bar {
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #a0a0a0;
        }
        .main-container {
            flex: 1;
            display: flex;
            gap: 20px;
            padding: 20px;
            overflow: hidden;
        }
        .panel {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .processes-panel {
            flex: 0 0 350px;
        }
        .process-card {
            background: #16213e;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #4caf50;
        }
        .process-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .process-name {
            font-weight: bold;
            font-size: 16px;
        }
        .process-info {
            font-size: 14px;
            color: #888;
        }
        .messages-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .messages-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .messages-container {
            flex: 1;
            overflow-y: auto;
            background: #0f0f1a;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
        }
        .message {
            padding: 8px;
            margin-bottom: 8px;
            border-radius: 4px;
            background: #1a1a2e;
            border-left: 3px solid #444;
        }
        .message.register { border-left-color: #ff9800; }
        .message.heartbeat { border-left-color: #4caf50; }
        .message.control { border-left-color: #f44336; }
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            color: #888;
            font-size: 12px;
        }
        .message-topic {
            font-weight: bold;
            color: #e0e0e0;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        .btn-danger {
            background: #f44336;
            color: white;
        }
        .btn-danger:hover {
            background: #d32f2f;
        }
        .global-actions {
            position: fixed;
            bottom: 20px;
            right: 20px;
        }
        .btn-large {
            padding: 12px 24px;
            font-size: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        ::-webkit-scrollbar {
            width: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #0a0a0a;
        }
        ::-webkit-scrollbar-thumb {
            background: #444;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌞 Sunshine Control Panel - Minimal Test</h1>
        <div class="status-bar">
            <span>Messages: <span id="message-count">0</span></span>
            <span>Processes: <span id="process-count">0</span></span>
            <span>Uptime: <span id="uptime">00:00:00</span></span>
        </div>
    </div>
    
    <div class="main-container">
        <div class="panel processes-panel">
            <h2>Registered Processes</h2>
            <div id="processes-container"></div>
        </div>
        
        <div class="panel messages-panel">
            <div class="messages-header">
                <h2>Message Stream</h2>
                <button class="btn btn-danger" onclick="clearMessages()">Clear</button>
            </div>
            <div id="messages-container" class="messages-container"></div>
        </div>
    </div>
    
    <div class="global-actions">
        <button class="btn btn-danger btn-large" onclick="shutdownAll()">Shutdown All</button>
    </div>
    
    <script>
        const socket = io();
        let startTime = Date.now();
        let messageCount = 0;
        
        // Update uptime
        setInterval(() => {
            const elapsed = Date.now() - startTime;
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            document.getElementById('uptime').textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
        
        socket.on('new_message', (message) => {
            addMessage(message);
            messageCount++;
            document.getElementById('message-count').textContent = messageCount;
        });
        
        socket.on('process_update', (processes) => {
            updateProcesses(processes);
        });
        
        function updateProcesses(processes) {
            const container = document.getElementById('processes-container');
            container.innerHTML = '';
            
            let count = 0;
            for (const [name, info] of Object.entries(processes)) {
                count++;
                const card = document.createElement('div');
                card.className = 'process-card';
                
                card.innerHTML = `
                    <div class="process-header">
                        <span class="process-name">${name}</span>
                        <button class="btn btn-danger" onclick="shutdownProcess('${name}')">Shutdown</button>
                    </div>
                    <div class="process-info">
                        PID: ${info.pid}<br>
                        Registered: ${new Date(info.registered_at).toLocaleTimeString()}<br>
                        Last seen: ${new Date(info.last_seen).toLocaleTimeString()}
                    </div>
                `;
                
                container.appendChild(card);
            }
            
            document.getElementById('process-count').textContent = count;
        }
        
        function addMessage(message) {
            const container = document.getElementById('messages-container');
            const messageEl = document.createElement('div');
            
            const topicClass = message.topic.includes('register') ? 'register' : 
                               message.topic.includes('heartbeat') ? 'heartbeat' : 
                               message.topic.includes('control') ? 'control' : '';
            
            messageEl.className = `message ${topicClass}`;
            
            const timestamp = new Date(message.timestamp).toLocaleTimeString();
            
            messageEl.innerHTML = `
                <div class="message-header">
                    <span><span class="message-topic">${message.topic}</span> from ${message.source}</span>
                    <span>${timestamp}</span>
                </div>
                <pre>${JSON.stringify(message.payload, null, 2)}</pre>
            `;
            
            container.insertBefore(messageEl, container.firstChild);
            
            // Keep only last 100 messages
            while (container.children.length > 100) {
                container.removeChild(container.lastChild);
            }
        }
        
        function clearMessages() {
            document.getElementById('messages-container').innerHTML = '';
            messageCount = 0;
            document.getElementById('message-count').textContent = '0';
        }
        
        function shutdownProcess(name) {
            socket.emit('shutdown_process', { process: name });
        }
        
        function shutdownAll() {
            if (confirm('Shutdown all processes?')) {
                socket.emit('shutdown_all');
            }
        }
        
        // Request initial state
        socket.emit('request_status');
    </script>
</body>
</html>
"""

class ControlPanel:
    def __init__(self):
        self.bus = MessageBus("control_panel")
        self.registered_processes = {}
        self.heartbeat_sequence = 0
        self.message_buffer = deque(maxlen=100)
        
        # Subscribe to all topics to monitor everything
        self.bus.subscribe_all()
        
        # Register handlers
        self.bus.register_handler(topics.PROCESS_REGISTER, self.handle_register)
        self.bus.register_handler(topics.HEARTBEAT_PONG, self.handle_pong)
        self.bus.register_handler("*", self.handle_all_messages)
        
        # Store instance for Flask access
        global control_panel_instance
        control_panel_instance = self
        
        # Start web server
        self.web_thread = threading.Thread(target=self._run_web_server, daemon=True)
        self.web_thread.start()
        
        print("🎮 Control Panel started")
        print("🌐 Web UI at http://localhost:5001")
        
        # Open browser after delay
        threading.Timer(2.0, lambda: webbrowser.open('http://localhost:5001')).start()
    
    def handle_all_messages(self, message):
        """Store all messages for web UI"""
        self.message_buffer.append(message)
        try:
            socketio.emit('new_message', message)
        except:
            pass
    
    def handle_register(self, message):
        """Handle process registration"""
        source = message["source"]
        payload = message["payload"]
        
        print(f"\n📥 Registration request from {source}")
        print(f"   PID: {payload['pid']}")
        
        # Register the process
        self.registered_processes[source] = {
            "pid": payload["pid"],
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
        
        # Send ACK
        self.bus.publish(topics.PROCESS_REGISTER_ACK, {
            "target": source,
            "accepted": True
        })
        
        print(f"✅ Sent ACK to {source}")
        
        # Update web UI
        try:
            socketio.emit('process_update', self.registered_processes)
        except:
            pass
    
    def handle_pong(self, message):
        """Handle heartbeat response"""
        source = message["source"]
        
        if source in self.registered_processes:
            self.registered_processes[source]["last_seen"] = datetime.now(timezone.utc).isoformat()
            print(f"💓 Heartbeat from {source}")
    
    def send_heartbeats(self):
        """Send heartbeat pings every 5 seconds"""
        while True:
            time.sleep(5)
            
            if self.registered_processes:
                self.heartbeat_sequence += 1
                self.bus.publish(topics.HEARTBEAT_PING, {
                    "sequence": self.heartbeat_sequence
                })
                print(f"\n📤 Sent heartbeat ping #{self.heartbeat_sequence}")
    
    def _run_web_server(self):
        """Run the Flask web server"""
        @app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)
        
        @app.route('/api/messages')
        def api_messages():
            return jsonify(list(self.message_buffer))
        
        @socketio.on('request_status')
        def handle_status_request():
            emit('process_update', self.registered_processes)
            for msg in list(self.message_buffer)[-10:]:
                emit('new_message', msg)
        
        @socketio.on('shutdown_process')
        def handle_shutdown_process(data):
            process = data.get('process')
            if process:
                self.bus.publish(topics.CONTROL_SHUTDOWN, {
                    "target": process,
                    "reason": "User requested via UI"
                })
        
        @socketio.on('shutdown_all')
        def handle_shutdown_all():
            self.bus.publish(topics.CONTROL_SHUTDOWN, {
                "target": "*",
                "reason": "User requested shutdown all via UI"
            })
        
        socketio.run(app, host='127.0.0.1', port=5001, debug=False, use_reloader=False, log_output=False)
    
    def run(self):
        """Main loop"""
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeats, daemon=True)
        heartbeat_thread.start()
        
        print("Control Panel ready, waiting for registrations...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nControl Panel shutting down...")
            self.bus.close()

# Global reference for Flask
control_panel_instance = None

if __name__ == "__main__":
    panel = ControlPanel()
    panel.run()

# Add terminal cleanup on shutdown
def cleanup_and_exit():
    """Cleanup and exit"""
    try:
        control_panel_instance.bus.close()
    except:
        pass
    print("\n✅ Control Panel shutdown complete")
    sys.exit(0)

# Update the run method to handle shutdown
if __name__ == "__main__":
    try:
        panel = ControlPanel()
        panel.run()
    except KeyboardInterrupt:
        cleanup_and_exit()

# Fix the control panel's own shutdown handling
def handle_control_shutdown(self, message):
    """Handle shutdown commands including self-shutdown"""
    payload = message["payload"]
    target = payload.get("target", "*")
    
    if target == "*" or target == "control_panel":
        print("🛑 Control Panel shutdown requested")
        self.running = False
        # Don't close bus here - let main loop handle it

# Add this handler in __init__ after other handlers
# self.bus.register_handler(topics.CONTROL_SHUTDOWN, self.handle_control_shutdown)
