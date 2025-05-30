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
