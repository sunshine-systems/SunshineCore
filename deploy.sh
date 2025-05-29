#!/bin/bash

echo "=========================================="
echo "Sunshine System Deployment Script"
echo "=========================================="

# Create root project directory
echo "Creating project structure..."
mkdir -p sunshine
cd sunshine

# Create main system directory
mkdir -p sunshine_systems

# Create subdirectories
mkdir -p sunshine_systems/auth
mkdir -p sunshine_systems/zeromq
mkdir -p sunshine_systems/subprocesses/control_panel
mkdir -p sunshine_systems/subprocesses/sunbox_interface
mkdir -p sunshine_systems/subprocesses/template_subprocess
mkdir -p sunshine_systems/templates/auth
mkdir -p sunshine_systems/templates/control_panel
mkdir -p sunshine_systems/utils
mkdir -p sunshine_systems/config

echo "Creating build scripts..."

# Create run_dev.sh
cat > run_dev.sh << 'EOF'
#!/bin/bash
echo "Starting Sunshine System in Development Mode"
echo "=========================================="

# Change to the sunshine_systems directory
cd sunshine_systems

# Activate pipenv environment and run with dev flag
pipenv run python main.py --devmode

# Return to root directory
cd ..

echo "System startup complete. All processes are now running independently."
EOF

# Make run_dev.sh executable
chmod +x run_dev.sh

# Create build_prod.sh
cat > build_prod.sh << 'EOF'
#!/bin/bash
echo "Building Sunshine System for Production"
echo "======================================"

# Change to the sunshine_systems directory
cd sunshine_systems

# Install dependencies
echo "Installing dependencies..."
pipenv install

# Build executable with PyInstaller
echo "Building executable..."
pipenv run pyinstaller --onefile --noconsole --add-data "templates:templates" main.py

# Return to root directory
cd ..

# Move the built executable to the root sunshine folder
echo "Moving executable to root folder..."
if [ -f "sunshine_systems/dist/main" ]; then
    mv sunshine_systems/dist/main sunshine_system
elif [ -f "sunshine_systems/dist/main.exe" ]; then
    mv sunshine_systems/dist/main.exe sunshine_system.exe
fi

echo "Build complete! Executable created in root folder"
EOF

# Make build_prod.sh executable
chmod +x build_prod.sh

echo "Creating main application files..."

# Create main.py
cat > sunshine_systems/main.py << 'EOF'
import sys
import os
import subprocess
import time
import socket
from auth.startup import start_auth_server
from subprocesses.registry import SUBPROCESS_REGISTRY, get_subprocess_folder_by_name
from utils.logger import crash_logger
from config.settings import *

def main():
    # Check if this is a subprocess call
    if '--registry' in sys.argv:
        registry_name = sys.argv[sys.argv.index('--registry') + 1]
        print(f"Starting subprocess: {registry_name}")
        run_subprocess(registry_name)
        return

    # Main startup process
    try:
        # Check for dev mode
        dev_mode = '--devmode' in sys.argv
        
        print("="*50)
        print("SUNSHINE SYSTEM STARTUP")
        print("="*50)
        
        # Phase 1: Authentication (BLOCKING)
        print("\nPhase 1: Authentication")
        print("-" * 25)
        auth_success = start_auth_server()
        
        if not auth_success:
            print("\n❌ Authentication failed or timed out. System will NOT start.")
            print("Please try again.")
            return
        
        # Phase 2: Start ZeroMQ Broker as subprocess
        print("\nPhase 2: Starting ZeroMQ Broker")
        print("-" * 35)
        try:
            start_zeromq_broker_subprocess(dev_mode)
            print("✅ ZeroMQ Broker subprocess started")
            
            # Wait for broker to be ready
            print("   Waiting for broker to initialize...")
            if wait_for_broker_ready():
                print("✅ ZeroMQ Broker is ready")
            else:
                print("❌ ZeroMQ Broker failed to initialize")
                return
                
        except Exception as e:
            print(f"❌ Failed to start ZeroMQ Broker: {e}")
            crash_logger("zeromq_broker_startup", e)
            return
        
        # Phase 3: Start registered subprocesses
        print("\nPhase 3: Starting Subprocesses")
        print("-" * 30)
        print(f"About to start {len(SUBPROCESS_REGISTRY)} subprocesses...")
        
        success_count = start_subprocesses(dev_mode)
        
        print(f"\n✅ Started {success_count}/{len(SUBPROCESS_REGISTRY)} subprocesses")
        print("\n" + "="*50)
        print("SUNSHINE SYSTEM STARTUP COMPLETE")
        print("="*50)
        print("\nAll systems are now running independently:")
        print("- ZeroMQ Broker (ports 5555/5556)")
        print("- Control Panel (http://127.0.0.1:2828)")
        print(f"- {len(SUBPROCESS_REGISTRY)} subprocess(es)")
        print("\nMain process exiting in 3 seconds...")
        
        # Brief pause then exit - all subprocesses continue running
        for i in range(3, 0, -1):
            print(f"   Exiting in {i}...")
            time.sleep(1)
        print("Main process terminated. All subprocesses continue running. ✅")
        
    except Exception as e:
        crash_logger("main_application", e)
        print(f"\n❌ Critical error in main application: {e}")
        print("Crash dump written to desktop.")
        sys.exit(1)

def run_subprocess(registry_name):
    """Run a specific subprocess based on registry name."""
    try:
        subprocess_folder = get_subprocess_folder_by_name(registry_name)
        if subprocess_folder:
            subprocess_path = os.path.join('subprocesses', subprocess_folder, 'main.py')
            
            if not os.path.exists(subprocess_path):
                print(f"❌ Subprocess main.py not found: {subprocess_path}")
                sys.exit(1)
            
            print(f"Executing subprocess: {subprocess_path}")
            
            # Execute the subprocess main.py directly
            with open(subprocess_path, 'r') as f:
                exec(f.read(), {'__name__': '__main__'})
        else:
            print(f"❌ Unknown subprocess: {registry_name}")
            sys.exit(1)
    except Exception as e:
        crash_logger(f"subprocess_{registry_name}", e)
        print(f"❌ Fatal error in {registry_name}: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

def start_zeromq_broker_subprocess(dev_mode):
    """Start ZeroMQ broker as an independent subprocess."""
    broker_path = os.path.join('zeromq', 'broker.py')
    
    if not os.path.exists(broker_path):
        raise FileNotFoundError(f"ZeroMQ broker not found: {broker_path}")
    
    cmd = [sys.executable, broker_path]
    
    if dev_mode:
        # Start with console window in dev mode
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()
            )
        else:  # Linux/Mac - use terminal emulator
            try:
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'x-terminal-emulator']
                for terminal in terminals:
                    try:
                        if terminal == 'gnome-terminal':
                            subprocess.Popen([terminal, '--', *cmd], cwd=os.getcwd())
                        else:
                            subprocess.Popen([terminal, '-e'] + cmd, cwd=os.getcwd())
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback to background process
                    print("   (Running ZeroMQ Broker in background - no terminal emulator found)")
                    subprocess.Popen(cmd, cwd=os.getcwd())
            except Exception:
                subprocess.Popen(cmd, cwd=os.getcwd())
    else:
        # Background process for production
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:  # Linux/Mac
            subprocess.Popen(cmd, cwd=os.getcwd())

def wait_for_broker_ready(timeout=10):
    """Wait for ZeroMQ broker to be ready by checking if ports are listening."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if broker ports are listening
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            result1 = sock1.connect_ex(('127.0.0.1', ZEROMQ_PORT))
            result2 = sock2.connect_ex(('127.0.0.1', ZEROMQ_PORT + 1))
            
            sock1.close()
            sock2.close()
            
            if result1 == 0 and result2 == 0:
                return True
                
        except Exception:
            pass
        
        time.sleep(0.5)
    
    return False

def start_subprocesses(dev_mode):
    """Start all registered subprocesses and return success count."""
    success_count = 0
    
    print(f"   Found {len(SUBPROCESS_REGISTRY)} processes in registry")
    
    for i, subprocess_config in enumerate(SUBPROCESS_REGISTRY, 1):
        try:
            print(f"  {i}. Starting {subprocess_config['name']} (folder: {subprocess_config['folder']})...")
            start_subprocess_with_registry(subprocess_config, dev_mode)
            print(f"     ✅ {subprocess_config['name']} started")
            success_count += 1
            print(f"     Sleeping 1 second before next subprocess...")
            time.sleep(1)  # Stagger startup
        except Exception as e:
            print(f"     ❌ Failed to start {subprocess_config['name']}: {e}")
            print(f"     Error details: {str(e)}")
            crash_logger(f"subprocess_startup_{subprocess_config['name']}", e)
            # Continue with other processes
            print(f"     Continuing with remaining processes...")
    
    print(f"   Subprocess startup loop completed. Success count: {success_count}")
    return success_count

def start_subprocess_with_registry(config, dev_mode):
    """Start a subprocess using the registry approach."""
    cmd = [sys.executable, 'main.py', '--registry', config['name']]
    
    print(f"     Command: {' '.join(cmd)}")
    
    if dev_mode and config.get('show_console', True):
        # Windows-specific console window creation
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()
            )
            print(f"     Started with PID: {process.pid}")
        else:  # Linux/Mac - use terminal emulator
            try:
                # Try different terminal emulators
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'x-terminal-emulator']
                for terminal in terminals:
                    try:
                        if terminal == 'gnome-terminal':
                            process = subprocess.Popen([terminal, '--', *cmd], cwd=os.getcwd())
                        else:
                            process = subprocess.Popen([terminal, '-e'] + cmd, cwd=os.getcwd())
                        print(f"     Started with terminal {terminal}, PID: {process.pid}")
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback to background process with output
                    print(f"     (Running {config['name']} in background - no terminal emulator found)")
                    process = subprocess.Popen(cmd, cwd=os.getcwd())
                    print(f"     Started in background, PID: {process.pid}")
            except Exception as e:
                print(f"     Terminal launch failed, using background: {e}")
                process = subprocess.Popen(cmd, cwd=os.getcwd())
                print(f"     Started in background, PID: {process.pid}")
    else:
        # Background process
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:  # Linux/Mac
            process = subprocess.Popen(cmd, cwd=os.getcwd())
        print(f"     Started in background, PID: {process.pid}")

if __name__ == "__main__":
    main()
EOF

# Create Pipfile
cat > sunshine_systems/Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
flask = "*"
flask-socketio = "*"
pyzmq = "*"
requests = "*"

[dev-packages]
pyinstaller = "*"

[requires]
python_version = "3.12"
EOF

echo "Creating authentication module..."

# Create auth/startup.py
cat > sunshine_systems/auth/startup.py << 'EOF'
from flask import Flask, render_template, request, jsonify
import threading
import time
import webbrowser
import os
from utils.process_manager import kill_process_on_port
from config.settings import AUTH_PORT

app = Flask(__name__, template_folder='../templates')

# Global flag to track authentication status
auth_completed = threading.Event()
flask_server = None

def start_auth_server():
    """Start authentication server and wait for user authentication."""
    # Kill any existing process on the port
    kill_process_on_port(AUTH_PORT)
    
    print("Starting authentication server...")
    
    # Start Flask server in thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Open browser automatically
    auth_url = f'http://127.0.0.1:{AUTH_PORT}/'
    print(f"Opening browser to: {auth_url}")
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually navigate to: {auth_url}")
    
    # Wait for authentication to complete
    print("Waiting for user authentication...")
    success = auth_completed.wait(timeout=300)  # 5 minute timeout
    
    if success:
        print("✅ Authentication successful!")
        # Give a moment for the shutdown response to be sent
        time.sleep(2)
        return True
    else:
        print("❌ Authentication timeout!")
        return False

def run_server():
    """Run Flask server."""
    global flask_server
    try:
        # Store server reference for shutdown
        flask_server = app
        app.run(host='127.0.0.1', port=AUTH_PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"Server error: {e}")

@app.route('/')
def index():
    return render_template('auth/index.html')

@app.route('/auth', methods=['POST'])
def authenticate():
    """Handle authentication request."""
    try:
        # Mock authentication - always accept
        print("User authentication received")
        
        # Set the authentication completed flag
        auth_completed.set()
        
        return jsonify({'status': 'success', 'message': 'Authentication successful'})
    except Exception as e:
        print(f"Authentication error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Handle shutdown request."""
    try:
        print("Shutting down auth server...")
        
        # Shutdown Flask server gracefully
        def shutdown_server():
            time.sleep(1)
            # Kill the process on this port to force shutdown
            kill_process_on_port(AUTH_PORT)
        
        threading.Thread(target=shutdown_server, daemon=True).start()
        return jsonify({'status': 'shutting_down'})
    except Exception as e:
        print(f"Shutdown error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
EOF

echo "Creating ZeroMQ broker..."

# Create zeromq/broker.py
cat > sunshine_systems/zeromq/broker.py << 'EOF'
import zmq
import sys
import os
import time
import threading

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import ZEROMQ_PORT
from utils.logger import crash_logger

def main():
    try:
        print("ZeroMQ Broker starting...")
        
        context = zmq.Context()
        
        # Frontend socket for publishers (subprocesses send messages here)
        frontend = context.socket(zmq.SUB)
        frontend.bind(f"tcp://*:{ZEROMQ_PORT}")
        frontend.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Backend socket for subscribers (subprocesses receive messages here)
        backend = context.socket(zmq.PUB)
        backend.bind(f"tcp://*:{ZEROMQ_PORT + 1}")
        
        print(f"✅ ZeroMQ Broker ready on ports {ZEROMQ_PORT}/{ZEROMQ_PORT + 1}")
        print("Message relay active. Press Ctrl+C to stop.")
        
        try:
            # Simple message relay - forwards all messages from publishers to subscribers
            zmq.proxy(frontend, backend)
        except KeyboardInterrupt:
            print("\nReceived interrupt signal...")
        except Exception as e:
            print(f"Broker error: {e}")
            crash_logger("zeromq_broker", e)
        finally:
            print("Shutting down ZeroMQ Broker...")
            frontend.close()
            backend.close()
            context.term()
            print("ZeroMQ Broker shutdown complete")
    
    except Exception as e:
        crash_logger("zeromq_broker_startup", e)
        print(f"Failed to start ZeroMQ Broker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "Creating subprocess registry..."

# Create subprocesses/registry.py
cat > sunshine_systems/subprocesses/registry.py << 'EOF'
SUBPROCESS_REGISTRY = [
    {
        'name': 'ControlPanel',
        'folder': 'control_panel',
        'critical': True,
        'show_console': True,  # Always show console for control panel in dev
    },
    {
        'name': 'SunBoxInterface',
        'folder': 'sunbox_interface',
        'critical': True,
        'show_console': True,
    },
    # Add additional subprocesses here as needed
    # To create a new subprocess:
    # 1. Copy the template_subprocess folder
    # 2. Rename it to your desired name
    # 3. Edit the main.py to set the process name
    # 4. Add entry here with folder name
    # {
    #     'name': 'MyNewProcess',
    #     'folder': 'my_new_process',
    #     'critical': False,
    #     'show_console': False,
    # },
]

def get_subprocess_folder_by_name(name):
    """Get subprocess folder by name from registry."""
    for config in SUBPROCESS_REGISTRY:
        if config['name'] == name:
            return config['folder']
    return None

# Debug: Print registry on import
print(f"DEBUG: Loaded {len(SUBPROCESS_REGISTRY)} processes from registry:")
for proc in SUBPROCESS_REGISTRY:
    print(f"  - {proc['name']} ({proc['folder']})")
EOF

echo "Creating base subprocess class..."

# Create subprocesses/base_subprocess.py
cat > sunshine_systems/subprocesses/base_subprocess.py << 'EOF'
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
        self.last_ping_time = time.time()
        self.shutdown_flag = threading.Event()
        self.registration_thread = None
        self.message_thread = None
        self.main_thread = None
        
    def start(self):
        """Start the subprocess with all required threads."""
        try:
            self.setup_zmq()
            
            # Start registration thread
            self.registration_thread = threading.Thread(target=self.registration_loop, daemon=True)
            self.registration_thread.start()
            
            # Start message handling thread
            self.message_thread = threading.Thread(target=self.message_loop, daemon=True)
            self.message_thread.start()
            
            # Start main process thread
            self.main_thread = threading.Thread(target=self.main_loop_wrapper, daemon=True)
            self.main_thread.start()
            
            # Keep main thread alive and monitor for shutdown
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
        self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
    
    def registration_loop(self):
        """Handle registration with ControlPanel."""
        attempts = 0
        max_attempts = 30
        
        while not self.registered and attempts < max_attempts:
            try:
                self.send_message(MSG_REGISTER, {
                    'process_name': self.process_name,
                    'process_id': self.process_id
                })
                
                print(f"{self.process_name}: Registration attempt {attempts + 1}")
                time.sleep(2)
                attempts += 1
                
            except Exception as e:
                print(f"{self.process_name}: Registration error: {e}")
                time.sleep(2)
                attempts += 1
        
        if not self.registered:
            print(f"{self.process_name}: Failed to register after {max_attempts} attempts. Shutting down.")
            self.shutdown()
    
    def message_loop(self):
        """Handle incoming ZeroMQ messages."""
        while not self.shutdown_flag.is_set():
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                message = json.loads(raw_message.decode('utf-8'))
                self.handle_message(message)
                
            except zmq.Again:
                continue  # No message received
            except Exception as e:
                print(f"{self.process_name}: Message handling error: {e}")
    
    def handle_message(self, message):
        """Process incoming messages."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Handle system messages
            if msg_type == MSG_REGISTER_ACK and sender == 'ControlPanel':
                if payload.get('process_name') == self.process_name:
                    self.registered = True
                    print(f"{self.process_name}: Registration acknowledged")
            
            elif msg_type == MSG_PING and sender == 'ControlPanel':
                self.last_ping_time = time.time()
                self.send_message(MSG_PONG, {'process_name': self.process_name})
            
            elif msg_type == MSG_SHUTDOWN:
                target = payload.get('target')
                if target == '*' or target == self.process_name:
                    print(f"{self.process_name}: Shutdown command received")
                    self.shutdown()
            
            # Handle custom messages
            else:
                self.handle_custom_message(message)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
    
    def handle_custom_message(self, message):
        """Override this method in subclasses to handle custom messages."""
        pass
    
    def main_loop_wrapper(self):
        """Wrapper for main loop with crash protection."""
        try:
            self.main_loop()
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            self.shutdown()
    
    def main_loop(self):
        """Override this method in subclasses for custom main loop logic."""
        while not self.shutdown_flag.is_set():
            # Default behavior: log every 5 seconds
            self.log_info(f"{self.process_name} main loop heartbeat")
            time.sleep(5)
    
    def monitor_health(self):
        """Monitor ping/pong health and shutdown if unhealthy."""
        while not self.shutdown_flag.is_set():
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:  # 15 seconds without ping
                    print(f"{self.process_name}: No ping received for 15 seconds. Shutting down.")
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
            self.publisher.send_string(json.dumps(message))
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
        print(f"{self.process_name}: Initiating shutdown...")
        self.shutdown_flag.set()
        
        # Close ZeroMQ connections
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
        
        print(f"{self.process_name}: Shutdown complete")
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

echo "Creating control panel subprocess..."

# Create subprocesses/control_panel/main.py
cat > sunshine_systems/subprocesses/control_panel/main.py << 'EOF'
import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import json
import time
from subprocesses.base_subprocess import BaseSubProcess
from utils.message_types import *
from utils.process_manager import kill_process_on_port
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
            # Kill any existing process on the port
            kill_process_on_port(CONTROL_PANEL_PORT)
            
            # Start Flask server
            self.start_flask_server()
            
            # Start base subprocess functionality
            super().start()
            
        except Exception as e:
            crash_logger("control_panel_startup", e)
            raise
    
    def start_flask_server(self):
        """Initialize and start Flask server with SocketIO."""
        template_folder = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
        self.flask_app = Flask(__name__, template_folder=template_folder)
        self.flask_app.config['SECRET_KEY'] = 'control_panel_secret'
        self.socketio = SocketIO(self.flask_app, cors_allowed_origins="*")
        
        @self.flask_app.route('/')
        def index():
            return render_template('control_panel/index.html')
        
        @self.socketio.on('connect')
        def handle_connect():
            print("Client connected to Control Panel")
            # Send current state to new client
            emit('processes_update', list(self.registered_processes.values()))
            emit('messages_update', self.message_history[-50:])  # Last 50 messages
        
        # Start Flask server in separate thread
        self.flask_thread = threading.Thread(
            target=lambda: self.socketio.run(
                self.flask_app, 
                host='127.0.0.1', 
                port=CONTROL_PANEL_PORT, 
                debug=False
            ),
            daemon=True
        )
        self.flask_thread.start()
        time.sleep(2)  # Allow server to start
        print(f"ControlPanel: Flask server started on port {CONTROL_PANEL_PORT}")
    
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
                    if self.socketio:
                        self.socketio.emit('processes_update', list(self.registered_processes.values()))
            
            elif msg_type == MSG_PONG:
                # Update process last seen time
                process_name = payload.get('process_name')
                if process_name in self.registered_processes:
                    self.registered_processes[process_name]['last_seen'] = time.time()
                    self.registered_processes[process_name]['status'] = 'active'
            
            # Store all messages for UI display
            self.message_history.append(message)
            if len(self.message_history) > 1000:  # Keep last 1000 messages
                self.message_history = self.message_history[-1000:]
            
            # Update UI with new message
            if self.socketio:
                self.socketio.emit('message_received', message)
                
        except Exception as e:
            crash_logger("control_panel_message_handling", e)
    
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
                if dead_processes and self.socketio:
                    self.socketio.emit('processes_update', list(self.registered_processes.values()))
                
                # Send heartbeat log
                self.log_info(f"ControlPanel monitoring {len(self.registered_processes)} processes")
                
                time.sleep(5)  # Ping every 5 seconds
                
        except Exception as e:
            crash_logger("control_panel_main_loop", e)
            self.shutdown()

def main():
    try:
        print("="*50)
        print("CONTROL PANEL STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        
        control_panel = ControlPanel()
        print("ControlPanel: Created successfully, starting...")
        control_panel.start()
    except Exception as e:
        crash_logger("control_panel", e)
        print(f"ControlPanel: Fatal error: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "Creating sunbox interface subprocess..."

# Create subprocesses/sunbox_interface/main.py
cat > sunshine_systems/subprocesses/sunbox_interface/main.py << 'EOF'
import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from subprocesses.base_subprocess import BaseSubProcess
from utils.message_types import *
from utils.logger import crash_logger
import time

class SunBoxInterface(BaseSubProcess):
    def __init__(self):
        super().__init__("SunBoxInterface")
        self.custom_data = {}
        print(f"SunBoxInterface: Initialized with PID {os.getpid()}")
    
    def handle_custom_message(self, message):
        """Handle custom messages specific to SunBoxInterface."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Example: Handle custom message types
            if msg_type == 'SUNBOX_COMMAND':
                self.handle_sunbox_command(payload)
            
            elif msg_type == MSG_LOG:
                # Process log messages from other components
                log_level = payload.get('level', 'INFO')
                log_message = payload.get('message', '')
                print(f"SunBoxInterface: Received log [{log_level}] from {sender}: {log_message}")
                
        except Exception as e:
            crash_logger("sunbox_interface_message_handling", e)
            print(f"SunBoxInterface: Error handling message: {e}")
    
    def handle_sunbox_command(self, payload):
        """Handle SunBox-specific commands."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            if command == 'store_data':
                key = data.get('key')
                value = data.get('value')
                if key:
                    self.custom_data[key] = value
                    self.log_info(f"SunBoxInterface: Stored data {key} = {value}")
                    print(f"SunBoxInterface: Stored data {key} = {value}")
            
            elif command == 'get_data':
                key = data.get('key')
                if key in self.custom_data:
                    # Send response back
                    self.send_message('SUNBOX_RESPONSE', {
                        'command': 'get_data',
                        'key': key,
                        'value': self.custom_data[key]
                    })
                    
        except Exception as e:
            crash_logger("sunbox_interface_command_handling", e)
            print(f"SunBoxInterface: Error handling command: {e}")
    
    def main_loop(self):
        """Custom main loop for SunBoxInterface."""
        try:
            counter = 0
            print("SunBoxInterface: Starting main loop...")
            
            while not self.shutdown_flag.is_set():
                counter += 1
                
                # Send periodic hello world log
                message = f"SunBoxInterface Hello World #{counter}"
                self.log_info(message)
                print(f"SunBoxInterface: {message}")
                
                # Example: Send custom data every 10 iterations
                if counter % 10 == 0:
                    status_msg = {
                        'iteration': counter,
                        'data_items': len(self.custom_data),
                        'status': 'running'
                    }
                    self.send_message('SUNBOX_STATUS', status_msg)
                    print(f"SunBoxInterface: Sent status update: {status_msg}")
                
                # Sleep for 5 seconds
                time.sleep(5)
                
        except Exception as e:
            crash_logger("sunbox_interface_main_loop", e)
            print(f"SunBoxInterface: Error in main loop: {e}")
            self.shutdown()

def main():
    try:
        print("="*50)
        print("SUNBOX INTERFACE STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        
        sunbox_interface = SunBoxInterface()
        print("SunBoxInterface: Created successfully, starting...")
        sunbox_interface.start()
    except Exception as e:
        crash_logger("sunbox_interface", e)
        print(f"SunBoxInterface: Fatal error: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "Creating template subprocess..."

# Create subprocesses/template_subprocess/main.py
cat > sunshine_systems/subprocesses/template_subprocess/main.py << 'EOF'
import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from subprocesses.base_subprocess import BaseSubProcess
from utils.message_types import *
from utils.logger import crash_logger
import time

class TemplateSubprocess(BaseSubProcess):
    def __init__(self):
        # CHANGE THIS: Set your subprocess name here
        super().__init__("TemplateSubprocess")
        
        # Add your custom initialization here
        self.custom_data = {}
        self.iteration_count = 0
    
    def handle_custom_message(self, message):
        """Handle custom messages specific to this subprocess."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Add your custom message handlers here
            if msg_type == 'CUSTOM_COMMAND':
                self.handle_custom_command(payload)
            
            elif msg_type == 'ANOTHER_MESSAGE_TYPE':
                self.handle_another_message(payload, sender)
            
            # Example: Log all received messages for debugging
            self.log_debug(f"Received {msg_type} from {sender}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
    
    def handle_custom_command(self, payload):
        """Handle custom command messages."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            # Add your command handling logic here
            if command == 'example_command':
                self.log_info(f"Received example command with data: {data}")
                
                # Example: Send response back
                self.send_message('CUSTOM_RESPONSE', {
                    'command': command,
                    'result': 'success',
                    'processed_data': data
                })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
    
    def handle_another_message(self, payload, sender):
        """Handle another type of message."""
        try:
            # Add your message handling logic here
            self.log_info(f"Handling another message from {sender}: {payload}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_another_message_handling", e)
    
    def main_loop(self):
        """Main processing loop for this subprocess."""
        try:
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Add your main processing logic here
                self.do_main_work()
                
                # Send periodic status updates
                if self.iteration_count % 10 == 0:
                    self.send_status_update()
                
                # Log heartbeat every 5 iterations
                if self.iteration_count % 5 == 0:
                    self.log_info(f"Template subprocess heartbeat #{self.iteration_count}")
                
                # Sleep between iterations
                time.sleep(5)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            self.shutdown()
    
    def do_main_work(self):
        """Your main processing work goes here."""
        try:
            # Replace this with your actual work logic
            # Example work:
            current_time = time.time()
            self.custom_data['last_run'] = current_time
            self.custom_data['iteration'] = self.iteration_count
            
            # Example: Process some data, make calculations, etc.
            # result = self.process_something()
            # self.handle_result(result)
            
        except Exception as e:
            crash_logger(f"{self.process_name}_main_work", e)
    
    def send_status_update(self):
        """Send status update to other processes."""
        try:
            self.send_message('STATUS_UPDATE', {
                'process_name': self.process_name,
                'iteration': self.iteration_count,
                'status': 'running',
                'data_items': len(self.custom_data),
                'timestamp': time.time()
            })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_update", e)

def main():
    try:
        # Create and start the subprocess
        subprocess = TemplateSubprocess()
        subprocess.start()
    except Exception as e:
        crash_logger("template_subprocess", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "Creating sunbox interface subprocess..."

# Create subprocesses/sunbox_interface/main.py
cat > sunshine_systems/subprocesses/sunbox_interface/main.py << 'EOF'
import sys
import os

print("SunBoxInterface: Starting imports...")

# Add parent directories to path for imports
parent_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, parent_dir)
print(f"SunBoxInterface: Added to path: {parent_dir}")

try:
    from subprocesses.base_subprocess import BaseSubProcess
    print("SunBoxInterface: BaseSubProcess imported successfully")
except Exception as e:
    print(f"SunBoxInterface: Failed to import BaseSubProcess: {e}")
    sys.exit(1)

try:    
    from utils.message_types import *
    print("SunBoxInterface: Message types imported successfully")
except Exception as e:
    print(f"SunBoxInterface: Failed to import message types: {e}")
    sys.exit(1)

try:
    from utils.logger import crash_logger
    print("SunBoxInterface: Logger imported successfully")
except Exception as e:
    print(f"SunBoxInterface: Failed to import logger: {e}")
    sys.exit(1)

import time

class SunBoxInterface(BaseSubProcess):
    def __init__(self):
        print("SunBoxInterface: Calling parent constructor...")
        super().__init__("SunBoxInterface")
        self.custom_data = {}
        print(f"SunBoxInterface: Initialized with PID {os.getpid()}")
    
    def handle_custom_message(self, message):
        """Handle custom messages specific to SunBoxInterface."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Example: Handle custom message types
            if msg_type == 'SUNBOX_COMMAND':
                self.handle_sunbox_command(payload)
            
            elif msg_type == MSG_LOG:
                # Process log messages from other components
                log_level = payload.get('level', 'INFO')
                log_message = payload.get('message', '')
                print(f"SunBoxInterface: Received log [{log_level}] from {sender}: {log_message}")
                
        except Exception as e:
            crash_logger("sunbox_interface_message_handling", e)
            print(f"SunBoxInterface: Error handling message: {e}")
    
    def handle_sunbox_command(self, payload):
        """Handle SunBox-specific commands."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            if command == 'store_data':
                key = data.get('key')
                value = data.get('value')
                if key:
                    self.custom_data[key] = value
                    self.log_info(f"SunBoxInterface: Stored data {key} = {value}")
                    print(f"SunBoxInterface: Stored data {key} = {value}")
            
            elif command == 'get_data':
                key = data.get('key')
                if key in self.custom_data:
                    # Send response back
                    self.send_message('SUNBOX_RESPONSE', {
                        'command': 'get_data',
                        'key': key,
                        'value': self.custom_data[key]
                    })
                    
        except Exception as e:
            crash_logger("sunbox_interface_command_handling", e)
            print(f"SunBoxInterface: Error handling command: {e}")
    
    def main_loop(self):
        """Custom main loop for SunBoxInterface."""
        try:
            counter = 0
            print("SunBoxInterface: Starting main loop...")
            
            while not self.shutdown_flag.is_set():
                counter += 1
                
                # Send periodic hello world log
                message = f"SunBoxInterface Hello World #{counter}"
                self.log_info(message)
                print(f"SunBoxInterface: {message}")
                
                # Example: Send custom data every 10 iterations
                if counter % 10 == 0:
                    status_msg = {
                        'iteration': counter,
                        'data_items': len(self.custom_data),
                        'status': 'running'
                    }
                    self.send_message('SUNBOX_STATUS', status_msg)
                    print(f"SunBoxInterface: Sent status update: {status_msg}")
                
                # Sleep for 5 seconds
                time.sleep(5)
                
        except Exception as e:
            crash_logger("sunbox_interface_main_loop", e)
            print(f"SunBoxInterface: Error in main loop: {e}")
            self.shutdown()

def main():
    try:
        print("="*50)
        print("SUNBOX INTERFACE STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        print(f"Python Path: {sys.path}")
        
        print("SunBoxInterface: Creating instance...")
        sunbox_interface = SunBoxInterface()
        print("SunBoxInterface: Created successfully, starting...")
        sunbox_interface.start()
        
    except Exception as e:
        crash_logger("sunbox_interface", e)
        print(f"SunBoxInterface: Fatal error: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)  # Wait 30 seconds if input fails
        sys.exit(1)

if __name__ == "__main__":
    print("SunBoxInterface: Script starting...")
    main()
EOF

echo "Creating template subprocess..."

# Create subprocesses/template_subprocess/main.py
cat > sunshine_systems/subprocesses/template_subprocess/main.py << 'EOF'
import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from subprocesses.base_subprocess import BaseSubProcess
from utils.message_types import *
from utils.logger import crash_logger
import time

class TemplateSubprocess(BaseSubProcess):
    def __init__(self):
        # CHANGE THIS: Set your subprocess name here
        super().__init__("TemplateSubprocess")
        
        # Add your custom initialization here
        self.custom_data = {}
        self.iteration_count = 0
    
    def handle_custom_message(self, message):
        """Handle custom messages specific to this subprocess."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Add your custom message handlers here
            if msg_type == 'CUSTOM_COMMAND':
                self.handle_custom_command(payload)
            
            elif msg_type == 'ANOTHER_MESSAGE_TYPE':
                self.handle_another_message(payload, sender)
            
            # Example: Log all received messages for debugging
            self.log_debug(f"Received {msg_type} from {sender}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
    
    def handle_custom_command(self, payload):
        """Handle custom command messages."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            # Add your command handling logic here
            if command == 'example_command':
                self.log_info(f"Received example command with data: {data}")
                
                # Example: Send response back
                self.send_message('CUSTOM_RESPONSE', {
                    'command': command,
                    'result': 'success',
                    'processed_data': data
                })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
    
    def handle_another_message(self, payload, sender):
        """Handle another type of message."""
        try:
            # Add your message handling logic here
            self.log_info(f"Handling another message from {sender}: {payload}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_another_message_handling", e)
    
    def main_loop(self):
        """Main processing loop for this subprocess."""
        try:
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Add your main processing logic here
                self.do_main_work()
                
                # Send periodic status updates
                if self.iteration_count % 10 == 0:
                    self.send_status_update()
                
                # Log heartbeat every 5 iterations
                if self.iteration_count % 5 == 0:
                    self.log_info(f"Template subprocess heartbeat #{self.iteration_count}")
                
                # Sleep between iterations
                time.sleep(5)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            self.shutdown()
    
    def do_main_work(self):
        """Your main processing work goes here."""
        try:
            # Replace this with your actual work logic
            # Example work:
            current_time = time.time()
            self.custom_data['last_run'] = current_time
            self.custom_data['iteration'] = self.iteration_count
            
            # Example: Process some data, make calculations, etc.
            # result = self.process_something()
            # self.handle_result(result)
            
        except Exception as e:
            crash_logger(f"{self.process_name}_main_work", e)
    
    def send_status_update(self):
        """Send status update to other processes."""
        try:
            self.send_message('STATUS_UPDATE', {
                'process_name': self.process_name,
                'iteration': self.iteration_count,
                'status': 'running',
                'data_items': len(self.custom_data),
                'timestamp': time.time()
            })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_update", e)

def main():
    try:
        # Create and start the subprocess
        subprocess = TemplateSubprocess()
        subprocess.start()
    except Exception as e:
        crash_logger("template_subprocess", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "Creating utility modules..."

# Create utils/__init__.py
touch sunshine_systems/utils/__init__.py

# Create utils/message_types.py
cat > sunshine_systems/utils/message_types.py << 'EOF'
# System Message Types
MSG_REGISTER = "REGISTER"
MSG_REGISTER_ACK = "REGISTER_ACK"
MSG_PING = "PING"
MSG_PONG = "PONG"
MSG_SHUTDOWN = "SHUTDOWN"
MSG_LOG = "LOG"

# Application Message Types
MSG_SUNBOX_COMMAND = "SUNBOX_COMMAND"
MSG_SUNBOX_RESPONSE = "SUNBOX_RESPONSE"
MSG_SUNBOX_STATUS = "SUNBOX_STATUS"

# Add additional message types as needed
EOF

# Create utils/logger.py
cat > sunshine_systems/utils/logger.py << 'EOF'
import os
import traceback
from datetime import datetime

def crash_logger(component_name, exception):
    """Log crash information to desktop file."""
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"sunshine_crash_{component_name}_{timestamp}.log"
    log_filepath = os.path.join(desktop_path, log_filename)
    
    try:
        with open(log_filepath, 'w') as f:
            f.write(f"Sunshine System Crash Report\n")
            f.write(f"Component: {component_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Exception: {str(exception)}\n\n")
            f.write(f"Full Traceback:\n")
            f.write(traceback.format_exc())
        
        print(f"Crash log written to: {log_filepath}")
    except Exception as e:
        print(f"Failed to write crash log: {e}")
EOF

# Create utils/process_manager.py
cat > sunshine_systems/utils/process_manager.py << 'EOF'
import subprocess
import time

def kill_process_on_port(port):
    """Kill any process using the specified port (Windows-specific)."""
    try:
        # Find process using the port
        result = subprocess.run(
            ['netstat', '-ano'], 
            capture_output=True, 
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                        print(f"Killed process {pid} on port {port}")
                        time.sleep(1)  # Allow port to be released
                    except subprocess.CalledProcessError:
                        print(f"Failed to kill process {pid}")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
EOF

echo "Creating configuration..."

# Create config/__init__.py
touch sunshine_systems/config/__init__.py

# Create config/settings.py
cat > sunshine_systems/config/settings.py << 'EOF'
# Port Configuration
AUTH_PORT = 2828
CONTROL_PANEL_PORT = 2828  # Same as auth since they run sequentially
ZEROMQ_PORT = 5555

# Application Settings
MAX_REGISTRATION_ATTEMPTS = 30
REGISTRATION_RETRY_INTERVAL = 2
PING_INTERVAL = 5
PING_TIMEOUT = 15
MAX_MESSAGE_HISTORY = 1000

# Logging Settings
LOG_TO_DESKTOP_ON_CRASH = True
MAX_LOG_MESSAGES = 1000
EOF

echo "Creating HTML templates..."

# Create templates/auth/index.html
cat > sunshine_systems/templates/auth/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunshine Authentication</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .auth-container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            min-width: 300px;
        }
        .logo {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 1rem;
        }
        .auth-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.1rem;
            border-radius: 5px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .auth-button:hover:not(:disabled) {
            transform: translateY(-2px);
        }
        .auth-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            margin-top: 1rem;
            padding: 0.5rem;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .countdown {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">Sunshine System</div>
        <p>Click to authenticate and start the system</p>
        <button class="auth-button" onclick="authenticate()">Authenticate</button>
        <div id="status" class="status"></div>
        <div id="countdown" class="countdown"></div>
    </div>

    <script>
        async function authenticate() {
            const button = document.querySelector('.auth-button');
            const status = document.getElementById('status');
            const countdown = document.getElementById('countdown');
            
            button.disabled = true;
            button.textContent = 'Authenticating...';
            status.style.display = 'none';
            countdown.style.display = 'none';
            
            try {
                const response = await fetch('/auth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    status.textContent = 'Authentication successful! Starting system...';
                    status.className = 'status success';
                    status.style.display = 'block';
                    
                    // Show countdown
                    countdown.style.display = 'block';
                    let timeLeft = 3;
                    countdown.textContent = `Closing window in ${timeLeft} seconds...`;
                    
                    const countdownInterval = setInterval(() => {
                        timeLeft--;
                        if (timeLeft > 0) {
                            countdown.textContent = `Closing window in ${timeLeft} seconds...`;
                        } else {
                            countdown.textContent = 'Closing window...';
                            clearInterval(countdownInterval);
                        }
                    }, 1000);
                    
                    // Send shutdown request then close window
                    setTimeout(async () => {
                        try {
                            await fetch('/shutdown', { 
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                }
                            });
                        } catch (e) {
                            // Server shutdown expected, ignore connection errors
                            console.log('Server shutdown initiated');
                        }
                        
                        // Close the browser tab/window
                        setTimeout(() => {
                            // Try multiple methods to close the window
                            try {
                                window.close();
                            } catch (e) {
                                // If window.close() doesn't work, try to navigate away
                                window.location = 'about:blank';
                            }
                        }, 500);
                    }, 3000);
                } else {
                    throw new Error(result.message || 'Authentication failed');
                }
            } catch (error) {
                console.error('Authentication error:', error);
                status.textContent = 'Authentication failed. Please try again.';
                status.className = 'status error';
                status.style.display = 'block';
                button.disabled = false;
                button.textContent = 'Authenticate';
                countdown.style.display = 'none';
            }
        }
        
        // Auto-focus the button when page loads
        window.addEventListener('load', () => {
            document.querySelector('.auth-button').focus();
        });
        
        // Allow Enter key to authenticate
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !document.querySelector('.auth-button').disabled) {
                authenticate();
            }
        });
    </script>
</body>
</html>
EOF

# Create templates/control_panel/index.html
cat > sunshine_systems/templates/control_panel/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunshine Control Panel</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.4/socket.io.js"></script>
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
    </style>
</head>
<body>
    <div class="header">
        <h1>Sunshine Control Panel</h1>
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
                        No processes registered
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
                        Waiting for messages...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let processes = [];
        let messages = [];
        
        socket.on('connect', function() {
            console.log('Connected to Control Panel');
        });
        
        socket.on('processes_update', function(data) {
            processes = data;
            updateProcessesList();
            updateStats();
        });
        
        socket.on('message_received', function(message) {
            messages.unshift(message);
            if (messages.length > 100) {
                messages = messages.slice(0, 100);
            }
            updateMessagesList();
            updateStats();
        });
        
        socket.on('messages_update', function(data) {
            messages = data.reverse();
            updateMessagesList();
            updateStats();
        });
        
        function updateProcessesList() {
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
        
        function updateMessagesList() {
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
        
        function updateStats() {
            document.getElementById('process-count').textContent = processes.length;
            document.getElementById('message-count').textContent = messages.length;
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
    </script>
</body>
</html>
EOF

echo ""
echo "=========================================="
echo "Sunshine System deployment complete!"
echo "=========================================="
echo ""
echo "Project structure created at: $(pwd)"
echo ""
echo "Next steps:"
echo "1. Install Python 3.12 and pipenv if not already installed"
echo "2. Navigate to sunshine_systems/ and run: pipenv install"
echo "3. Run the development version with: ./run_dev.sh"
echo "4. Build production version with: ./build_prod.sh"
echo ""
echo "Authentication Flow:"
echo "- System will automatically open your browser"
echo "- Click 'Authenticate' to proceed"
echo "- System will start all processes after authentication"
echo "- Control Panel will be available at http://127.0.0.1:2828"
echo ""
echo "The system includes:"
echo "- Complete folder-based subprocess architecture"
echo "- ZeroMQ message broker with TCP communication"
echo "- Web-based authentication with automatic browser opening"
echo "- Real-time control panel with process monitoring"
echo "- Health monitoring with ping/pong"
echo "- Comprehensive crash logging to desktop"
echo "- Template for creating new subprocesses"
echo ""
echo "Scripts created:"
echo "- run_dev.sh (Development mode with console windows)"
echo "- build_prod.sh (Production build with PyInstaller)"
echo ""
echo "Happy coding! 🌞"