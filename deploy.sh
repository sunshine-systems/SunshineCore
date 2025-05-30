#!/bin/bash

echo "================================================"
echo "Creating CometExample with Corona Framework"
echo "================================================"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p CometExample/comet/src/corona
echo "✅ Created CometExample directory structure"

# Create Pipfile in comet directory
cat > CometExample/comet/Pipfile << 'EOF'
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
pyzmq = "*"

[dev-packages]
pyinstaller = "*"

[requires]
python_version = "3.12"
EOF
echo "✅ Created comet/Pipfile"

# Create crash handler
cat > CometExample/comet/src/corona/crash_handler.py << 'EOF'
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

def setup_crash_handler(comet_name: str):
    """Setup exception handler that logs crashes to Documents/Sunshine/Crash."""
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        # Don't log KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Get crash directory
        if os.name == 'nt':  # Windows
            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
        else:  # Linux/Mac
            documents = os.path.join(os.path.expanduser('~'), 'Documents')
        
        crash_dir = Path(documents) / 'Sunshine' / 'Crash'
        crash_dir.mkdir(parents=True, exist_ok=True)
        
        # Create crash file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        crash_file = crash_dir / f"{comet_name}_{timestamp}.log"
        
        # Write crash log
        with open(crash_file, 'w') as f:
            f.write(f"Comet Crash Report\n")
            f.write(f"==================\n")
            f.write(f"Comet: {comet_name}\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"\nException:\n")
            f.write(f"{exc_type.__name__}: {exc_value}\n")
            f.write(f"\nTraceback:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        print(f"💥 Crash dump saved to: {crash_file}")
        
        # Also print to console
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Set as the default exception handler
    sys.excepthook = handle_exception

def log_crash(comet_name: str, error_msg: str, exception: Exception = None):
    """Manually log a crash or error."""
    if os.name == 'nt':  # Windows
        documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
    else:  # Linux/Mac
        documents = os.path.join(os.path.expanduser('~'), 'Documents')
    
    crash_dir = Path(documents) / 'Sunshine' / 'Crash'
    crash_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    crash_file = crash_dir / f"{comet_name}_{timestamp}.log"
    
    with open(crash_file, 'w') as f:
        f.write(f"Comet Error Report\n")
        f.write(f"==================\n")
        f.write(f"Comet: {comet_name}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Error: {error_msg}\n")
        if exception:
            f.write(f"\nException Details:\n")
            f.write(f"{type(exception).__name__}: {str(exception)}\n")
            f.write(f"\nTraceback:\n")
            f.write(traceback.format_exc())
EOF
echo "✅ Created comet/src/corona/crash_handler.py"

# Create SolarFlare
cat > CometExample/comet/src/corona/SolarFlare.py << 'EOF'
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class SolarFlare:
    """Message format for inter-Comet communication."""
    timestamp: datetime
    name: str  # Sender's name
    type: str  # Message type
    payload: Any  # Flexible payload
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'datetime': self.timestamp.isoformat(),
            'message_type': self.type,
            'sender': self.name,
            'payload': self.payload
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create SolarFlare from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['datetime']),
            name=data['sender'],
            type=data['message_type'],
            payload=data.get('payload', {})
        )
EOF
echo "✅ Created comet/src/corona/SolarFlare.py"

# Create Satellite
cat > CometExample/comet/src/corona/Satellite.py << 'EOF'
import zmq
import json
import threading
import time
from queue import Queue
from .SolarFlare import SolarFlare

class Satellite:
    """ZeroMQ connection handler for Comet communication."""
    
    def __init__(self, comet_name: str, in_queue: Queue, out_queue: Queue, subscribe_filters: list):
        self.comet_name = comet_name
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.subscribe_filters = subscribe_filters
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.running = True
        
    def connect(self):
        """Establish ZeroMQ connections."""
        # Publisher socket
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect("tcp://localhost:5555")
        
        # Subscriber socket
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://localhost:5556")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.RCVTIMEO, 100)
        
        # Give sockets time to connect
        time.sleep(0.5)
    
    def start(self):
        """Start receiver and sender threads."""
        receiver = threading.Thread(target=self._receive_loop, daemon=True)
        sender = threading.Thread(target=self._send_loop, daemon=True)
        receiver.start()
        sender.start()
    
    def _receive_loop(self):
        """Receive messages and filter them into the in_queue."""
        while self.running:
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                data = json.loads(raw_message.decode('utf-8'))
                flare = SolarFlare.from_dict(data)
                
                # Filter messages based on subscribe list
                if "*" in self.subscribe_filters or flare.type in self.subscribe_filters:
                    self.in_queue.put(flare)
                    
            except zmq.Again:
                time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"Satellite receive error: {e}")
    
    def _send_loop(self):
        """Send messages from out_queue."""
        while self.running:
            try:
                if not self.out_queue.empty():
                    flare = self.out_queue.get()
                    message = json.dumps(flare.to_dict())
                    self.publisher.send_string(message)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Satellite send error: {e}")
    
    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        time.sleep(0.5)
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
EOF
echo "✅ Created comet/src/corona/Satellite.py"

# Create CometCore
cat > CometExample/comet/src/corona/CometCore.py << 'EOF'
import sys
import os
import time
import threading
from queue import Queue
from datetime import datetime
from .SolarFlare import SolarFlare
from .Satellite import Satellite
from .crash_handler import setup_crash_handler, log_crash

class CometCore:
    """Core functionality for all Comets."""
    
    # System message types
    MSG_REGISTER = "REGISTER"
    MSG_REGISTER_ACK = "REGISTER_ACK"
    MSG_PING = "PING"
    MSG_PONG = "PONG"
    MSG_SHUTDOWN = "SHUTDOWN"
    MSG_SHUTDOWN_ACK = "SHUTDOWN_ACK"
    
    def __init__(self, name: str, subscribe_to: list, in_queue: Queue, out_queue: Queue,
                 on_startup=None, on_shutdown=None, main_loop=None):
        self.name = name
        self.pid = os.getpid()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.system_queue = Queue()  # For system messages
        self.subscribe_to = subscribe_to
        self.on_startup = on_startup
        self.on_shutdown = on_shutdown
        self.main_loop = main_loop
        self.registered = False
        self.running = True
        self.last_ping_time = time.time()
        self.dev_mode = "--dev" in sys.argv
        
        # Setup crash handler
        setup_crash_handler(self.name)
        
        # Hide console in production mode
        if not self.dev_mode and os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0
                )
            except:
                pass
        
        # All system messages we need to see
        system_messages = [
            self.MSG_REGISTER_ACK,
            self.MSG_PING,
            self.MSG_SHUTDOWN
        ]
        
        # Combine user filters with system messages
        all_filters = list(set(subscribe_to + system_messages))
        
        # Initialize satellite
        self.satellite = Satellite(
            self.name,
            self.system_queue,
            self.out_queue,
            all_filters if "*" not in subscribe_to else ["*"]
        )
    
    def start(self):
        """Start the Comet."""
        try:
            print(f"🌟 {self.name} starting (PID: {self.pid})")
            
            # Connect to ZeroMQ
            self.satellite.connect()
            self.satellite.start()
            
            # Start system message handler
            system_thread = threading.Thread(target=self._handle_system_messages, daemon=True)
            system_thread.start()
            
            # Call startup hook
            if self.on_startup:
                self.on_startup()
            
            # Register with ControlPanel
            if not self._register():
                print(f"❌ {self.name} failed to register")
                log_crash(self.name, "Failed to register with ControlPanel")
                self._shutdown()
                return
            
            print(f"✅ {self.name} registered successfully")
            
            # Start health monitor
            health_thread = threading.Thread(target=self._monitor_health, daemon=True)
            health_thread.start()
            
            # Run main loop
            if self.main_loop:
                self.main_loop()
            else:
                # Default main loop
                while self.running:
                    time.sleep(1)
                    
        except Exception as e:
            print(f"❌ {self.name} error: {e}")
            log_crash(self.name, f"Fatal error during startup: {e}", e)
            self._shutdown()
    
    def _register(self):
        """Register with ControlPanel."""
        max_attempts = 30
        
        for attempt in range(max_attempts):
            # Send registration
            reg_flare = SolarFlare(
                timestamp=datetime.now(),
                name=self.name,
                type=self.MSG_REGISTER,
                payload={'process_name': self.name, 'process_id': self.pid}
            )
            self.out_queue.put(reg_flare)
            
            # Wait for ACK
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.registered:
                    return True
                time.sleep(0.1)
            
            print(f"{self.name}: Registration attempt {attempt + 1}/{max_attempts}")
        
        return False
    
    def _handle_system_messages(self):
        """Handle system messages separately from user messages."""
        while self.running:
            try:
                if not self.system_queue.empty():
                    flare = self.system_queue.get()
                    
                    # Route to user queue if it's a subscribed message
                    if flare.type in self.subscribe_to or "*" in self.subscribe_to:
                        self.in_queue.put(flare)
                    
                    # Handle system messages
                    if flare.type == self.MSG_REGISTER_ACK:
                        if flare.payload.get('process_name') == self.name:
                            self.registered = True
                    
                    elif flare.type == self.MSG_PING:
                        if flare.name == 'ControlPanel':
                            self.last_ping_time = time.time()
                            pong = SolarFlare(
                                timestamp=datetime.now(),
                                name=self.name,
                                type=self.MSG_PONG,
                                payload={
                                    'process_name': self.name,
                                    'process_id': self.pid,
                                    'timestamp': time.time()
                                }
                            )
                            self.out_queue.put(pong)
                    
                    elif flare.type == self.MSG_SHUTDOWN:
                        target = flare.payload.get('target')
                        if target == '*' or target == self.name:
                            # Send ACK
                            ack = SolarFlare(
                                timestamp=datetime.now(),
                                name=self.name,
                                type=self.MSG_SHUTDOWN_ACK,
                                payload={
                                    'process_name': self.name,
                                    'process_id': self.pid,
                                    'shutdown_target': target,
                                    'timestamp': time.time()
                                }
                            )
                            self.out_queue.put(ack)
                            time.sleep(0.5)
                            self._shutdown()
                
                time.sleep(0.01)
                
            except Exception as e:
                error_msg = f"{self.name} system message error: {e}"
                print(error_msg)
                log_crash(self.name, error_msg, e)
    
    def _monitor_health(self):
        """Monitor connection health."""
        while self.running:
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:
                    error_msg = f"No ping for {int(time_since_ping)}s, shutting down"
                    print(f"⚠️ {self.name}: {error_msg}")
                    log_crash(self.name, error_msg)
                    self._shutdown()
                    break
            time.sleep(1)
    
    def _shutdown(self):
        """Shutdown the Comet."""
        print(f"🛑 {self.name} shutting down...")
        self.running = False
        
        if self.on_shutdown:
            try:
                self.on_shutdown()
            except Exception as e:
                log_crash(self.name, f"Error in shutdown hook: {e}", e)
        
        self.satellite.shutdown()
        time.sleep(0.5)
        sys.exit(0)
EOF
echo "✅ Created comet/src/corona/CometCore.py"

# Create __init__.py
cat > CometExample/comet/src/corona/__init__.py << 'EOF'
from .SolarFlare import SolarFlare
from .Satellite import Satellite
from .CometCore import CometCore
from .crash_handler import setup_crash_handler, log_crash

__all__ = ['SolarFlare', 'Satellite', 'CometCore', 'setup_crash_handler', 'log_crash']
EOF
echo "✅ Created comet/src/corona/__init__.py"

# Create main.py
cat > CometExample/comet/src/main.py << 'EOF'
#!/usr/bin/env python3
import time
from queue import Queue
from datetime import datetime
from corona import CometCore, SolarFlare

# Queues for communication
in_queue = Queue()
out_queue = Queue()

# State for our Comet
custom_data = {}
iteration_count = 0

def on_startup():
    """Called when Comet starts up."""
    print("🚀 CometExample starting up!")
    print("This Comet demonstrates the new architecture")

def on_shutdown():
    """Called when Comet shuts down."""
    print("👋 CometExample shutting down gracefully")

def main_loop():
    """Main processing loop."""
    global iteration_count
    
    print("🔄 CometExample main loop started")
    
    while True:
        # Check for incoming messages
        if not in_queue.empty():
            flare = in_queue.get()
            
            # Skip system messages (already handled by CometCore)
            if flare.type in ['PING', 'PONG', 'REGISTER', 'REGISTER_ACK']:
                continue
                
            print(f"📨 Received {flare.type} from {flare.name}")
            
            # Handle custom message types
            if flare.type == 'CUSTOM_COMMAND':
                handle_custom_command(flare)
            elif flare.type == 'DATA_REQUEST':
                handle_data_request(flare)
        
        # Do periodic work
        iteration_count += 1
        
        # Every 20 seconds, send a status update
        if iteration_count % 20 == 0:
            send_status_update()
        
        # Every 5 seconds, log activity
        if iteration_count % 5 == 0:
            log_flare = SolarFlare(
                timestamp=datetime.now(),
                name="CometExample",
                type="LOG",
                payload={
                    'level': 'INFO',
                    'message': f'CometExample iteration #{iteration_count}'
                }
            )
            out_queue.put(log_flare)
            print(f"📝 CometExample iteration #{iteration_count}")
        
        time.sleep(1)

def handle_custom_command(flare):
    """Handle custom commands."""
    command = flare.payload.get('command')
    data = flare.payload.get('data', {})
    
    if command == 'store_data':
        key = data.get('key')
        value = data.get('value')
        if key:
            custom_data[key] = value
            print(f"💾 Stored data: {key} = {value}")
            
            # Send confirmation
            response = SolarFlare(
                timestamp=datetime.now(),
                name="CometExample",
                type="CUSTOM_RESPONSE",
                payload={
                    'command': 'store_data',
                    'status': 'success',
                    'key': key
                }
            )
            out_queue.put(response)

def handle_data_request(flare):
    """Handle data requests."""
    key = flare.payload.get('key')
    
    if key in custom_data:
        response = SolarFlare(
            timestamp=datetime.now(),
            name="CometExample",
            type="DATA_RESPONSE",
            payload={
                'key': key,
                'value': custom_data[key]
            }
        )
        out_queue.put(response)
        print(f"📤 Sent data: {key} = {custom_data[key]}")

def send_status_update():
    """Send periodic status updates."""
    status = SolarFlare(
        timestamp=datetime.now(),
        name="CometExample",
        type="STATUS_UPDATE",
        payload={
            'iteration': iteration_count,
            'data_items': len(custom_data),
            'status': 'running',
            'timestamp': time.time()
        }
    )
    out_queue.put(status)
    print("📊 Sent status update")

if __name__ == "__main__":
    # Create and start the Comet
    comet = CometCore(
        name="CometExample",
        subscribe_to=["CUSTOM_COMMAND", "DATA_REQUEST", "STATUS_REQUEST"],
        in_queue=in_queue,
        out_queue=out_queue,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        main_loop=main_loop
    )
    
    comet.start()
EOF
echo "✅ Created comet/src/main.py"

# Create run_dev.sh at root level
cat > CometExample/run_dev.sh << 'EOF'
#!/bin/bash
echo "🌟 Running CometExample in development mode"
echo "==========================================="

# Navigate to the comet directory
cd "$(dirname "$0")/comet"

# Check if virtual environment exists
if [ ! -d ".venv" ] && ! pipenv --venv &>/dev/null; then
    echo "Creating virtual environment..."
    pipenv install
fi

# Run with --dev flag
echo "Starting CometExample with console window..."
pipenv run python src/main.py --dev
EOF
chmod +x CometExample/run_dev.sh
echo "✅ Created run_dev.sh"

# Create build_prod.sh at root level
cat > CometExample/build_prod.sh << 'EOF'
#!/bin/bash
echo "🔨 Building CometExample"
echo "======================="

# Navigate to the comet directory
cd "$(dirname "$0")/comet"

# Install dependencies including dev
echo "Installing dependencies..."
pipenv install --dev

# Build with PyInstaller
echo "Building executable..."
pipenv run pyinstaller --onefile --name CometExample src/main.py

# Move the executable to the parent dist folder
cd ..
mkdir -p dist
mv comet/dist/CometExample* dist/

echo ""
echo "✅ Build complete!"
echo "📦 Executable: dist/CometExample.exe"
echo ""
echo "To install in Sunshine:"
echo "1. Copy dist/CometExample.exe to:"
echo "   - Windows: %USERPROFILE%\Documents\Sunshine\plugins\"
echo "   - Mac/Linux: ~/Documents/Sunshine/plugins/"
echo "2. Start Sunshine normally"
echo ""
echo "Crash logs will be saved to:"
echo "   - Windows: %USERPROFILE%\Documents\Sunshine\Crash\"
echo "   - Mac/Linux: ~/Documents/Sunshine/Crash/"
EOF
chmod +x CometExample/build_prod.sh
echo "✅ Created build_prod.sh"

# Create install.bat at root level
cat > CometExample/install.bat << 'EOF'
@echo off
echo Installing CometExample to Sunshine...

if not exist dist\CometExample.exe (
    echo Error: CometExample.exe not found. Please run build_prod.sh first.
    pause
    exit /b 1
)

set PLUGIN_DIR=%USERPROFILE%\Documents\Sunshine\plugins

if not exist "%PLUGIN_DIR%" (
    echo Creating plugins directory...
    mkdir "%PLUGIN_DIR%"
)

echo Copying CometExample.exe to %PLUGIN_DIR%...
copy /Y dist\CometExample.exe "%PLUGIN_DIR%\"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Installation complete!
    echo CometExample has been installed to Sunshine.
    echo.
    echo Crash logs will be saved to:
    echo %USERPROFILE%\Documents\Sunshine\Crash\
) else (
    echo.
    echo Installation failed!
)

pause
EOF
echo "✅ Created install.bat"

# Create install.sh at root level
cat > CometExample/install.sh << 'EOF'
#!/bin/bash
echo "Installing CometExample to Sunshine..."

if [ ! -f dist/CometExample ]; then
    echo "Error: CometExample not found. Please run build_prod.sh first."
    exit 1
fi

PLUGIN_DIR="$HOME/Documents/Sunshine/plugins"

if [ ! -d "$PLUGIN_DIR" ]; then
    echo "Creating plugins directory..."
    mkdir -p "$PLUGIN_DIR"
fi

echo "Copying CometExample to $PLUGIN_DIR..."
cp dist/CometExample "$PLUGIN_DIR/"
chmod +x "$PLUGIN_DIR/CometExample"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Installation complete!"
    echo "CometExample has been installed to Sunshine."
    echo ""
    echo "Crash logs will be saved to:"
    echo "$HOME/Documents/Sunshine/Crash/"
else
    echo ""
    echo "❌ Installation failed!"
fi
EOF
chmod +x CometExample/install.sh
echo "✅ Created install.sh"

# Create README.md at root level
cat > CometExample/README.md << 'EOF'
# CometExample

A demonstration Comet for the Sunshine system using the Corona framework.

## What is a Comet?

A Comet is a standalone executable that communicates with the Sunshine system via ZeroMQ messages (SolarFlares). Each Comet:

- Runs as an independent process
- Automatically registers with the Control Panel
- Responds to health checks (ping/pong)
- Can subscribe to specific message types
- Handles graceful shutdown
- Logs crashes to `Documents/Sunshine/Crash/`

## Structure

```
CometExample/
├── run_dev.sh        # Development runner (shows console)
├── build_prod.sh     # Production build script
├── install.bat       # Windows installer
├── install.sh        # Mac/Linux installer
├── README.md         # This file
└── comet/            # Comet application
    ├── Pipfile       # Python dependencies
    └── src/
        ├── main.py   # Your Comet logic goes here
        └── corona/   # Comet framework (Corona)
            ├── CometCore.py     # Core functionality
            ├── SolarFlare.py    # Message format
            ├── Satellite.py     # ZeroMQ connector
            └── crash_handler.py # Crash logging
```

## Development

1. **Install dependencies:**
   ```bash
   cd comet
   pipenv install
   cd ..
   ```

2. **Run in development mode:**
   ```bash
   ./run_dev.sh
   ```
   This shows a console window for debugging.

3. **Modify `comet/src/main.py`** to implement your functionality.

## Building

1. **Build the executable:**
   ```bash
   ./build_prod.sh
   ```

2. **Install in Sunshine (automatic):**
   - Windows: Run `install.bat`
   - Mac/Linux: Run `./install.sh`

   Or manually copy to:
   - Windows: `%USERPROFILE%\Documents\Sunshine\plugins\`
   - Mac/Linux: `~/Documents/Sunshine/plugins/`

## Crash Handling

All crashes are automatically logged to:
- Windows: `%USERPROFILE%\Documents\Sunshine\Crash\`
- Mac/Linux: `~/Documents/Sunshine/Crash/`

Log files are named: `CometName_YYYYMMDD_HHMMSS.log`

## Creating Your Own Comet

1. Copy this entire directory
2. Rename it to your Comet name
3. Update the name in `comet/src/main.py`
4. Implement your logic in the `main_loop()` function
5. Subscribe to the message types you need

## Message Types

Your Comet can subscribe to any message types. Common ones include:

- `LOG` - Log messages from any Comet
- `STATUS_UPDATE` - Status updates
- Custom types you define

System messages (handled automatically by Corona):
- `REGISTER` / `REGISTER_ACK` - Registration
- `PING` / `PONG` - Health checks
- `SHUTDOWN` / `SHUTDOWN_ACK` - Shutdown commands

## Example Usage

```python
# In your main_loop():

# Send a message
flare = SolarFlare(
    timestamp=datetime.now(),
    name="YourComet",
    type="CUSTOM_MESSAGE",
    payload={"data": "value"}
)
out_queue.put(flare)

# Receive messages
if not in_queue.empty():
    flare = in_queue.get()
    print(f"Got {flare.type} from {flare.name}")
```

## Corona Framework

The Corona framework handles all the complex distributed system logic:
- **CometCore**: Manages lifecycle, registration, health checks
- **Satellite**: Handles ZeroMQ communication
- **SolarFlare**: Standard message format
- **crash_handler**: Automatic crash logging

This lets you focus on your Comet's unique functionality!
EOF
echo "✅ Created README.md"

# Create .gitignore
cat > CometExample/.gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual Environment
comet/.venv/
comet/Pipfile.lock

# Distribution
dist/
build/
*.egg-info/

# PyInstaller
*.spec

# Logs
*.log

# OS
.DS_Store
Thumbs.db
EOF
echo "✅ Created .gitignore"

echo ""
echo "================================================"
echo "✅ CometExample Created Successfully!"
echo "================================================"
echo ""
echo "Structure created:"
echo "CometExample/"
echo "├── run_dev.sh        # Run in dev mode"
echo "├── build_prod.sh     # Build executable"
echo "├── install.bat       # Windows installer"
echo "├── install.sh        # Linux/Mac installer"
echo "├── README.md         # Documentation"
echo "└── comet/            # Application code"
echo "    ├── Pipfile       # Dependencies"
echo "    └── src/"
echo "        ├── main.py   # Your code here"
echo "        └── corona/   # Framework"
echo ""
echo "Next steps:"
echo "1. Test it:"
echo "   cd CometExample"
echo "   ./run_dev.sh"
echo ""
echo "2. Build it:"
echo "   ./build_prod.sh"
echo ""
echo "3. Install it:"
echo "   Windows: Run install.bat"
echo "   Mac/Linux: Run ./install.sh"
echo ""
echo "The Corona framework is ready! 🌟"