#!/bin/bash

echo "=========================================="
echo "Add Shutdown Acknowledgment & UI Update"
echo "=========================================="

cd sunshine/sunshine_systems

echo "Adding SHUTDOWN_ACK message type..."

# Add SHUTDOWN_ACK to message types
cat >> utils/message_types.py << 'EOF'
MSG_SHUTDOWN_ACK = "SHUTDOWN_ACK"
EOF

echo ""
echo "Updating base_subprocess to send SHUTDOWN_ACK..."

# Update base_subprocess.py to send SHUTDOWN_ACK
cat > subprocesses/base_subprocess.py << 'EOF'
import zmq
import json
import threading
import time
import sys
import os
from datetime import datetime
from utils.message_types import *
from utils.logger import crash_logger
from config.settings import ZEROMQ_PORT

class BaseSubProcess:
    def __init__(self, process_name):
        self.process_name = process_name
        self.process_id = os.getpid()
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.registered = False
        self.registration_complete = threading.Event()
        self.last_ping_time = time.time()
        self.shutdown_flag = threading.Event()
        self.message_thread = None
        self.main_thread = None
        self.on_message_sent = None  # Callback for sent messages
        
    def start(self):
        """Start the subprocess with proper registration flow."""
        try:
            print(f"{self.process_name}: Setting up ZeroMQ connections...")
            self.setup_zmq()
            
            # Start message handling thread first
            print(f"{self.process_name}: Starting message handler...")
            self.message_thread = threading.Thread(target=self.message_loop, daemon=True)
            self.message_thread.start()
            
            # Give message handler time to start
            time.sleep(0.5)
            
            # Perform registration (BLOCKING)
            print(f"{self.process_name}: Starting registration process...")
            if not self.register_with_control_panel():
                print(f"{self.process_name}: Registration failed. Shutting down.")
                self.shutdown()
                return
            
            print(f"{self.process_name}: Registration successful! Starting main loop...")
            
            # Start main process thread
            self.main_thread = threading.Thread(target=self.main_loop_wrapper, daemon=True)
            self.main_thread.start()
            
            # Monitor health in main thread
            self.monitor_health()
            
        except Exception as e:
            crash_logger(f"{self.process_name}_startup", e)
            raise
    
    def setup_zmq(self):
        """Initialize ZeroMQ connections."""
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect(f"tcp://localhost:{ZEROMQ_PORT}")
        
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://localhost:{ZEROMQ_PORT + 1}")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout for non-blocking
        
        # Give sockets time to connect
        time.sleep(0.5)
    
    def register_with_control_panel(self):
        """Register with ControlPanel and wait for acknowledgment."""
        max_attempts = 30
        retry_interval = 2
        
        for attempt in range(max_attempts):
            try:
                # Send registration message
                self.send_message(MSG_REGISTER, {
                    'process_name': self.process_name,
                    'process_id': self.process_id
                })
                
                print(f"{self.process_name}: Registration attempt {attempt + 1}/{max_attempts}")
                
                # Wait for acknowledgment
                if self.registration_complete.wait(timeout=retry_interval):
                    return True
                
            except Exception as e:
                print(f"{self.process_name}: Registration error: {e}")
        
        return False
    
    def message_loop(self):
        """Handle incoming ZeroMQ messages."""
        print(f"{self.process_name}: Message handler started")
        
        while not self.shutdown_flag.is_set():
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                message = json.loads(raw_message.decode('utf-8'))
                self.handle_message(message)
                
            except zmq.Again:
                # No message available
                time.sleep(0.01)
            except Exception as e:
                if not self.shutdown_flag.is_set():
                    print(f"{self.process_name}: Message handling error: {e}")
    
    def handle_message(self, message):
        """Process incoming messages."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Handle system messages
            if msg_type == MSG_REGISTER_ACK:
                # Check if this ACK is for us
                if payload.get('process_name') == self.process_name:
                    self.registered = True
                    self.registration_complete.set()
                    print(f"{self.process_name}: ✅ Registration acknowledged by {sender}")
            
            elif msg_type == MSG_PING:
                # Respond to all pings from ControlPanel
                if sender == 'ControlPanel':
                    self.last_ping_time = time.time()
                    self.send_message(MSG_PONG, {
                        'process_name': self.process_name,
                        'process_id': self.process_id,
                        'timestamp': time.time()
                    })
                    print(f"{self.process_name}: 🏓 PONG sent to {sender}")
            
            elif msg_type == MSG_SHUTDOWN:
                target = payload.get('target')
                if target == '*' or target == self.process_name:
                    print(f"{self.process_name}: 🛑 Shutdown command received from {sender}")
                    
                    # Send shutdown acknowledgment before shutting down
                    self.send_message(MSG_SHUTDOWN_ACK, {
                        'process_name': self.process_name,
                        'process_id': self.process_id,
                        'shutdown_target': target,
                        'timestamp': time.time()
                    })
                    print(f"{self.process_name}: 📤 Sent SHUTDOWN_ACK")
                    
                    # Give time for the ACK to be sent
                    time.sleep(0.5)
                    
                    # Now shutdown
                    self.shutdown()
            
            # Let subclasses handle other messages
            else:
                self.handle_custom_message(message)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
            print(f"{self.process_name}: Error handling message: {e}")
    
    def handle_custom_message(self, message):
        """Override this method in subclasses to handle custom messages."""
        pass
    
    def main_loop_wrapper(self):
        """Wrapper for main loop with crash protection."""
        try:
            self.main_loop()
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            print(f"{self.process_name}: Main loop crashed: {e}")
            self.shutdown()
    
    def main_loop(self):
        """Override this method in subclasses for custom main loop logic."""
        while not self.shutdown_flag.is_set():
            # Default behavior: log heartbeat every 10 seconds
            self.log_info(f"{self.process_name} heartbeat - running main loop")
            time.sleep(10)
    
    def monitor_health(self):
        """Monitor ping/pong health and shutdown if unhealthy."""
        print(f"{self.process_name}: Health monitor started")
        
        while not self.shutdown_flag.is_set():
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:  # 15 seconds without ping
                    print(f"{self.process_name}: ⚠️  No ping received for {int(time_since_ping)} seconds. Shutting down.")
                    self.shutdown()
                    break
            
            time.sleep(1)
    
    def send_message(self, message_type, payload):
        """Send a message via ZeroMQ."""
        message = {
            'datetime': datetime.now().isoformat(),
            'message_type': message_type,
            'sender': self.process_name,
            'payload': payload
        }
        
        try:
            msg_json = json.dumps(message)
            self.publisher.send_string(msg_json)
            
            # Log outgoing messages (except routine ping/pong)
            if message_type not in [MSG_PING, MSG_PONG]:
                print(f"{self.process_name}: 📤 Sent {message_type}")
            
            # Notify callback if set (for ControlPanel to capture its own messages)
            if self.on_message_sent:
                self.on_message_sent(message)
            
        except Exception as e:
            print(f"{self.process_name}: Failed to send message: {e}")
    
    # Convenience logging methods
    def log_info(self, message):
        """Send an INFO log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'INFO',
            'message': message
        })
    
    def log_warning(self, message):
        """Send a WARNING log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'WARNING', 
            'message': message
        })
    
    def log_error(self, message):
        """Send an ERROR log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'ERROR',
            'message': message
        })
    
    def log_debug(self, message):
        """Send a DEBUG log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'DEBUG',
            'message': message
        })
    
    def shutdown(self):
        """Gracefully shutdown the subprocess."""
        print(f"{self.process_name}: 🛑 Initiating shutdown...")
        self.shutdown_flag.set()
        
        # Give threads time to finish
        time.sleep(0.5)
        
        # Close ZeroMQ connections
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
        
        print(f"{self.process_name}: 🛑 Shutdown complete")
        sys.exit(0)

def main():
    """Entry point for subprocess execution."""
    # This should be overridden by subclasses
    try:
        process = BaseSubProcess("GenericProcess")
        process.start()
    except Exception as e:
        crash_logger("base_subprocess", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo ""
echo "Updating ControlPanel to handle SHUTDOWN_ACK..."

# Update control_panel to handle SHUTDOWN_ACK
cat > subprocesses/control_panel/main.py << 'EOF'
import sys
import os

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.path.dirname(os.path.abspath(sys.argv[0]))
parent_dir = os.path.join(current_dir, '..', '..')
parent_dir = os.path.abspath(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import json
import time
from datetime import datetime
from subprocesses.base_subprocess import BaseSubProcess
from utils.message_types import *
from utils.logger import crash_logger
from config.settings import CONTROL_PANEL_PORT

class ControlPanel(BaseSubProcess):
    def __init__(self):
        super().__init__("ControlPanel")
        self.registered_processes = {}
        self.message_history = []
        self.flask_app = None
        self.socketio = None
        self.flask_thread = None
        
        # Set callback to capture our own sent messages
        self.on_message_sent = self.add_message_to_history
        
        print(f"ControlPanel: Initialized with PID {os.getpid()}")
        
    def start(self):
        """Override start to include Flask server."""
        try:
            # Start Flask server WITHOUT killing port (auth server already shut down)
            self.start_flask_server()
            
            # Start base subprocess functionality
            super().start()
            
        except Exception as e:
            crash_logger("control_panel_startup", e)
            raise
    
    def start_flask_server(self):
        """Initialize and start Flask server with SocketIO."""
        templates_path = os.path.join(os.getcwd(), 'templates')
        if not os.path.exists(templates_path):
            templates_path = os.path.join(parent_dir, 'templates')
        
        print(f"ControlPanel: Using templates folder: {templates_path}")
        
        self.flask_app = Flask(__name__, template_folder=templates_path)
        self.flask_app.config['SECRET_KEY'] = 'control_panel_secret'
        self.socketio = SocketIO(self.flask_app, cors_allowed_origins="*", logger=False, engineio_logger=False)
        
        @self.flask_app.route('/')
        def index():
            return render_template('control_panel/index.html')
        
        @self.socketio.on('connect')
        def handle_connect():
            print("ControlPanel: Client connected to SocketIO")
            emit('processes_update', list(self.registered_processes.values()))
            emit('messages_update', self.message_history[-200:])  # Send last 200 messages
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("ControlPanel: Client disconnected from SocketIO")
        
        @self.socketio.on('send_shutdown')
        def handle_shutdown_request(data):
            target = data.get('target', '*')
            print(f"ControlPanel: Shutdown request received for: {target}")
            self.send_message(MSG_SHUTDOWN, {'target': target})
            return {'status': 'sent'}
        
        # Start Flask server in separate thread
        self.flask_thread = threading.Thread(
            target=lambda: self.socketio.run(
                self.flask_app, 
                host='127.0.0.1', 
                port=CONTROL_PANEL_PORT, 
                debug=False,
                allow_unsafe_werkzeug=True
            ),
            daemon=True
        )
        self.flask_thread.start()
        time.sleep(2)
        print(f"ControlPanel: Flask server started on port {CONTROL_PANEL_PORT}")
    
    def emit_to_clients(self, event, data):
        """Safely emit to all connected clients."""
        try:
            if self.socketio:
                self.socketio.emit(event, data)
        except Exception as e:
            print(f"ControlPanel: Error emitting {event}: {e}")
    
    def add_message_to_history(self, message):
        """Add a message to history and emit to UI."""
        self.message_history.append(message)
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-1000:]
        
        # Emit to UI
        self.emit_to_clients('message_received', message)
    
    def handle_custom_message(self, message):
        """Handle ControlPanel-specific messages."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            if msg_type == MSG_REGISTER:
                # Handle process registration
                process_name = payload.get('process_name')
                process_id = payload.get('process_id')
                
                if process_name and process_id:
                    self.registered_processes[process_name] = {
                        'name': process_name,
                        'pid': process_id,
                        'status': 'active',
                        'last_seen': time.time(),
                        'registered_at': message.get('datetime')
                    }
                    
                    # Send acknowledgment specifically to this process
                    self.send_message(MSG_REGISTER_ACK, {
                        'process_name': process_name,
                        'status': 'registered'
                    })
                    
                    print(f"ControlPanel: ✅ Registered process {process_name} (PID: {process_id})")
                    
                    # Update UI
                    self.emit_to_clients('processes_update', list(self.registered_processes.values()))
            
            elif msg_type == MSG_PONG:
                # Update process last seen time
                process_name = payload.get('process_name')
                if process_name in self.registered_processes:
                    self.registered_processes[process_name]['last_seen'] = time.time()
                    self.registered_processes[process_name]['status'] = 'active'
                    print(f"ControlPanel: 🏓 PONG received from {process_name}")
            
            elif msg_type == MSG_SHUTDOWN_ACK:
                # Handle shutdown acknowledgment
                process_name = payload.get('process_name')
                if process_name in self.registered_processes:
                    print(f"ControlPanel: 📤 SHUTDOWN_ACK received from {process_name}")
                    # Mark process as shutting down
                    self.registered_processes[process_name]['status'] = 'shutting_down'
                    
                    # Update UI immediately
                    self.emit_to_clients('processes_update', list(self.registered_processes.values()))
                    
                    # Remove from registered processes after a short delay
                    def remove_process():
                        time.sleep(1)
                        if process_name in self.registered_processes:
                            del self.registered_processes[process_name]
                            print(f"ControlPanel: 🗑️  Removed {process_name} from registry")
                            self.emit_to_clients('processes_update', list(self.registered_processes.values()))
                    
                    threading.Thread(target=remove_process, daemon=True).start()
            
            # Store ALL incoming messages
            self.add_message_to_history(message)
                
        except Exception as e:
            crash_logger("control_panel_message_handling", e)
            print(f"ControlPanel: Error in handle_custom_message: {e}")
    
    def main_loop(self):
        """ControlPanel main loop with ping/pong monitoring."""
        try:
            print("ControlPanel: 🟢 Main loop started - will send PINGs every 5 seconds")
            
            # ControlPanel doesn't need to register with itself
            self.registered = True
            self.registered_processes["ControlPanel"] = {
                'name': 'ControlPanel',
                'pid': self.process_id,
                'status': 'active',
                'last_seen': time.time(),
                'registered_at': datetime.now().isoformat()
            }
            
            ping_count = 0
            
            while not self.shutdown_flag.is_set():
                current_time = time.time()
                ping_count += 1
                
                # Send ping to all processes (including self)
                print(f"\nControlPanel: 🏓 PING #{ping_count} to all processes")
                self.send_message(MSG_PING, {
                    'timestamp': current_time,
                    'ping_number': ping_count
                })
                
                # Check for dead processes
                dead_processes = []
                for process_name, process_info in self.registered_processes.items():
                    if process_name != "ControlPanel" and process_info['status'] == 'active':
                        time_since_seen = current_time - process_info['last_seen']
                        if time_since_seen > 15:  # 15 seconds timeout
                            print(f"ControlPanel: ⚠️  Process {process_name} appears dead ({int(time_since_seen)}s since last PONG)")
                            dead_processes.append(process_name)
                            process_info['status'] = 'dead'
                
                # Remove dead processes
                for process_name in dead_processes:
                    del self.registered_processes[process_name]
                    print(f"ControlPanel: 🗑️  Removed dead process: {process_name}")
                
                # Update UI if there were changes
                if dead_processes:
                    self.emit_to_clients('processes_update', list(self.registered_processes.values()))
                
                # Log active processes count
                active_count = len([p for p in self.registered_processes.values() if p['status'] == 'active'])
                print(f"ControlPanel: 📊 Active processes: {active_count}")
                
                # Sleep for 5 seconds before next ping
                time.sleep(5)
                
        except Exception as e:
            crash_logger("control_panel_main_loop", e)
            print(f"ControlPanel: Error in main_loop: {e}")
            self.shutdown()

def main():
    try:
        print("="*50)
        print("CONTROL PANEL STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        
        control_panel = ControlPanel()
        control_panel.start()
    except Exception as e:
        crash_logger("control_panel", e)
        print(f"ControlPanel: Fatal error: {e}")
        import traceback
        traceback.print_exc()
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo ""
echo "Updating UI to show process status changes..."

# Update the updateProcesses function to show status
sed -i 's/<div class="process-status ${process.status !== '\''active'\'' ? '\''dead'\'' : '\'''\''}/& style="${process.status === '\''shutting_down'\'' ? '\''background: var(--warning)'\'' : '\'''\''}"/' templates/control_panel/index.html

# Actually, let's update the whole process rendering to be clearer
cat > templates/control_panel/update_processes.js << 'EOF'
// This is just the updateProcesses function update
function updateProcesses() {
    const container = document.getElementById('processes-list');
    const activeCount = processes.filter(p => p.status === 'active').length;
    
    document.getElementById('process-count').textContent = activeCount;
    
    container.innerHTML = processes.map(process => {
        let statusColor = '';
        let statusText = '';
        
        if (process.status === 'active') {
            statusColor = 'var(--success)';
            statusText = ' (Active)';
        } else if (process.status === 'shutting_down') {
            statusColor = 'var(--warning)';
            statusText = ' (Shutting Down)';
        } else if (process.status === 'dead') {
            statusColor = 'var(--danger)';
            statusText = ' (Dead)';
        }
        
        return `
            <div class="process" style="opacity: ${process.status === 'active' ? '1' : '0.6'}">
                <span class="process-name">${process.name}${statusText}</span>
                <div class="process-status" style="background: ${statusColor}"></div>
            </div>
        `;
    }).join('');
}
EOF

echo ""
echo "Applying the process status update to the HTML..."

# Update the HTML file to show status changes
python3 << 'PYTHON_EOF'
# Read the HTML file
with open('templates/control_panel/index.html', 'r') as f:
    content = f.read()

# Find and replace the updateProcesses function
import re

# Define the new updateProcesses function
new_function = '''        // Update processes
        function updateProcesses() {
            const container = document.getElementById('processes-list');
            const activeCount = processes.filter(p => p.status === 'active').length;
            
            document.getElementById('process-count').textContent = activeCount;
            
            container.innerHTML = processes.map(process => {
                let statusColor = '';
                let statusText = '';
                
                if (process.status === 'active') {
                    statusColor = 'var(--success)';
                    statusText = '';
                } else if (process.status === 'shutting_down') {
                    statusColor = 'var(--warning)';
                    statusText = ' (Shutting Down)';
                } else if (process.status === 'dead') {
                    statusColor = 'var(--danger)';
                    statusText = ' (Dead)';
                }
                
                return `
                    <div class="process" style="opacity: ${process.status === 'active' ? '1' : '0.6'}">
                        <span class="process-name">${process.name}${statusText}</span>
                        <div class="process-status" style="background: ${statusColor}"></div>
                    </div>
                `;
            }).join('');
        }'''

# Replace the updateProcesses function
pattern = r'// Update processes\s*function updateProcesses\(\) {[^}]*}\s*}\s*}\)\.join\(\'\'\);\s*}'
content = re.sub(pattern, new_function, content, flags=re.DOTALL)

# Write back
with open('templates/control_panel/index.html', 'w') as f:
    f.write(content)

print("✅ Updated HTML file with process status display")
PYTHON_EOF

# Clean up temp file
rm -f templates/control_panel/update_processes.js

echo ""
echo "=========================================="
echo "Shutdown ACK & UI Update Complete!"
echo "=========================================="
echo ""
echo "Changes made:"
echo "✅ Added MSG_SHUTDOWN_ACK message type"
echo "✅ Processes send SHUTDOWN_ACK before shutting down"
echo "✅ ControlPanel marks process as 'shutting_down' on ACK"
echo "✅ UI shows process status: Active, Shutting Down, or Dead"
echo "✅ Process removed from list after shutdown completes"
echo ""
echo "Now when you shutdown a specific process:"
echo "1. Process receives SHUTDOWN command"
echo "2. Process sends SHUTDOWN_ACK"
echo "3. UI shows process as '(Shutting Down)' in orange"
echo "4. Process completes shutdown"
echo "5. Process disappears from UI"
echo ""
echo "This is the final patch - your system is complete! 🎉"