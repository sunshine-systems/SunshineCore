import sys
import os

# Add parent directories to path for imports - handle both exec and direct execution
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
        # Find templates folder relative to the working directory
        templates_path = os.path.join(os.getcwd(), 'templates')
        if not os.path.exists(templates_path):
            # Try relative to parent directory
            templates_path = os.path.join(parent_dir, 'templates')
        
        print(f"ControlPanel: Using templates folder: {templates_path}")
        
        self.flask_app = Flask(__name__, template_folder=templates_path)
        self.flask_app.config['SECRET_KEY'] = 'control_panel_secret'
        self.socketio = SocketIO(self.flask_app, cors_allowed_origins="*", logger=True, engineio_logger=True)
        
        @self.flask_app.route('/')
        def index():
            return render_template('control_panel/index.html')
        
        @self.socketio.on('connect')
        def handle_connect():
            print("ControlPanel: Client connected to SocketIO")
            print(f"ControlPanel: Sending {len(self.registered_processes)} processes to client")
            print(f"ControlPanel: Sending {len(self.message_history)} messages to client")
            
            # Send current state to new client
            emit('processes_update', list(self.registered_processes.values()))
            emit('messages_update', self.message_history[-50:])  # Last 50 messages
            
            print("ControlPanel: Initial data sent to client")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("ControlPanel: Client disconnected from SocketIO")
        
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
        time.sleep(2)  # Allow server to start
        print(f"ControlPanel: Flask server started on port {CONTROL_PANEL_PORT}")
    
    def emit_to_clients(self, event, data):
        """Safely emit to all connected clients."""
        try:
            if self.socketio:
                print(f"ControlPanel: Emitting {event} to clients: {data}")
                self.socketio.emit(event, data)
            else:
                print("ControlPanel: SocketIO not available for emit")
        except Exception as e:
            print(f"ControlPanel: Error emitting {event}: {e}")
    
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
                    
                    # Send acknowledgment
                    self.send_message(MSG_REGISTER_ACK, {
                        'process_name': process_name,
                        'status': 'registered'
                    })
                    
                    print(f"ControlPanel: Registered process {process_name} (PID: {process_id})")
                    
                    # Update UI
                    self.emit_to_clients('processes_update', list(self.registered_processes.values()))
            
            elif msg_type == MSG_PONG:
                # Update process last seen time
                process_name = payload.get('process_name')
                if process_name in self.registered_processes:
                    self.registered_processes[process_name]['last_seen'] = time.time()
                    self.registered_processes[process_name]['status'] = 'active'
                    # Don't emit on every pong to avoid spam
            
            # Store all messages for UI display
            self.message_history.append(message)
            if len(self.message_history) > 1000:  # Keep last 1000 messages
                self.message_history = self.message_history[-1000:]
            
            # Update UI with new message (limit frequency)
            if msg_type not in [MSG_PING, MSG_PONG]:  # Don't spam UI with ping/pong
                self.emit_to_clients('message_received', message)
                
        except Exception as e:
            crash_logger("control_panel_message_handling", e)
            print(f"ControlPanel: Error in handle_custom_message: {e}")
    
    def main_loop(self):
        """ControlPanel main loop with ping/pong and health monitoring."""
        try:
            print("ControlPanel: Starting main loop...")
            
            while not self.shutdown_flag.is_set():
                current_time = time.time()
                
                # Send ping to all registered processes
                if self.registered_processes:
                    self.send_message(MSG_PING, {'timestamp': current_time})
                
                # Check for dead processes
                dead_processes = []
                for process_name, process_info in self.registered_processes.items():
                    if current_time - process_info['last_seen'] > 15:  # 15 seconds timeout
                        print(f"ControlPanel: Process {process_name} appears dead. Marking for removal.")
                        dead_processes.append(process_name)
                        process_info['status'] = 'dead'
                        
                        # Kill the process
                        try:
                            import os
                            import signal
                            os.kill(process_info['pid'], signal.SIGTERM)
                        except:
                            pass
                
                # Remove dead processes
                for process_name in dead_processes:
                    del self.registered_processes[process_name]
                
                # Update UI if there were changes
                if dead_processes:
                    print(f"ControlPanel: Updating UI after removing {len(dead_processes)} dead processes")
                    self.emit_to_clients('processes_update', list(self.registered_processes.values()))
                
                # Send heartbeat log
                self.log_info(f"ControlPanel monitoring {len(self.registered_processes)} processes")
                
                time.sleep(5)  # Ping every 5 seconds
                
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
        print(f"Python Path: {sys.path[:3]}...")  # Show first 3 entries
        
        control_panel = ControlPanel()
        print("ControlPanel: Created successfully, starting...")
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
