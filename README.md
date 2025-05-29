# Sunshine System Architecture

## Overview

The Sunshine System is a distributed Windows application built with Python 3.12 that manages multiple independent subprocesses through a ZeroMQ message broker architecture. The system provides web-based authentication, real-time process monitoring, health checking, and inter-process communication.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Main Process  │    │   ZeroMQ Broker  │    │  Control Panel  │
│   (Startup)     │    │  (Message Relay) │    │   (Web UI)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
        ┌─────────────────┐          ┌─────────────────┐
        │ SunBoxInterface │          │ Additional      │
        │ (Worker Process)│          │ Subprocesses... │
        └─────────────────┘          └─────────────────┘
```

## 🚀 Startup Flow

### Phase 1: Authentication
1. **Flask Authentication Server** starts on port 2828
2. **Browser opens automatically** to authentication page
3. **User clicks "Authenticate"** (mock authentication - always succeeds)
4. **Browser window closes** and auth server shuts down

### Phase 2: ZeroMQ Broker
1. **Independent subprocess** starts the message broker
2. **TCP ports 5555/5556** are bound for pub/sub messaging
3. **Health check** confirms broker is ready

### Phase 3: Subprocess Registry
1. **Registry enumeration** reads all configured subprocesses
2. **Each subprocess** starts in its own console window (dev mode)
3. **Main process exits** leaving all subprocesses running independently

## 📁 Project Structure

```
sunshine/
├── run_dev.sh                    # Development launcher
├── build_prod.sh                 # Production build script
└── sunshine_systems/
    ├── main.py                   # Main entry point & subprocess router
    ├── Pipfile                   # Python dependencies
    ├── auth/
    │   └── startup.py            # Flask authentication server
    ├── zeromq/
    │   └── broker.py             # ZeroMQ TCP message broker
    ├── subprocesses/
    │   ├── registry.py           # Subprocess configuration
    │   ├── base_subprocess.py    # Base class for all subprocesses
    │   ├── control_panel/
    │   │   └── main.py           # Web-based monitoring & management
    │   ├── sunbox_interface/
    │   │   └── main.py           # Example worker subprocess
    │   └── template_subprocess/
    │       └── main.py           # Template for new subprocesses
    ├── templates/
    │   ├── auth/
    │   │   └── index.html        # Authentication web page
    │   └── control_panel/
    │       └── index.html        # Real-time monitoring dashboard
    ├── utils/
    │   ├── message_types.py      # Standard message definitions
    │   ├── logger.py             # Crash logging to desktop
    │   └── process_manager.py    # Windows process utilities
    └── config/
        └── settings.py           # Application configuration
```

## 🔄 Process Communication

### Message Format
All ZeroMQ messages use standardized JSON format:

```json
{
    "datetime": "2025-05-29T14:43:45.152908",
    "message_type": "REGISTER",
    "sender": "SunBoxInterface",
    "payload": {
        "process_name": "SunBoxInterface",
        "process_id": 18100
    }
}
```

### System Message Types

| Message Type | Direction | Purpose |
|--------------|-----------|---------|
| `REGISTER` | Subprocess → ControlPanel | Process registration request |
| `REGISTER_ACK` | ControlPanel → Subprocess | Registration acknowledgment |
| `PING` | ControlPanel → All | Health check probe |
| `PONG` | Subprocess → ControlPanel | Health check response |
| `SHUTDOWN` | ControlPanel → Target | Graceful shutdown command |
| `LOG` | Any → All | Log message broadcast |

### Communication Flow

1. **Registration Phase**:
   - New subprocess sends `REGISTER` with name and PID
   - ControlPanel responds with `REGISTER_ACK`
   - Process is added to monitoring list

2. **Health Monitoring**:
   - ControlPanel sends `PING` every 5 seconds
   - All registered processes respond with `PONG`
   - Non-responsive processes (15s timeout) are terminated

3. **Message Broadcasting**:
   - Any process can send messages to all others
   - ZeroMQ broker relays all messages to all subscribers
   - ControlPanel displays messages in real-time web UI

## 🖥️ Control Panel Features

### Web Dashboard (http://127.0.0.1:2828)
- **Real-time process monitoring** - Live status of all subprocesses
- **Message stream** - Live view of all inter-process messages
- **Process statistics** - Count of active processes and messages
- **Connection status** - WebSocket connection indicator
- **Debug information** - Real-time event logging

### SocketIO Events
- `processes_update` - Updates process list in UI
- `message_received` - Displays new messages in real-time
- `connect/disconnect` - Connection status management

## 🔧 Development Workflow

### Running the System
```bash
# Development mode (with console windows)
./run_dev.sh

# Production build
./build_prod.sh
```

### Creating New Subprocesses

1. **Copy Template**:
   ```bash
   cp -r subprocesses/template_subprocess subprocesses/my_new_process
   ```

2. **Edit Configuration**:
   ```python
   # In subprocesses/my_new_process/main.py
   super().__init__("MyNewProcess")  # Change process name
   ```

3. **Register Process**:
   ```python
   # In subprocesses/registry.py
   SUBPROCESS_REGISTRY = [
       # ... existing processes ...
       {
           'name': 'MyNewProcess',
           'folder': 'my_new_process',
           'critical': False,
           'show_console': True,
       },
   ]
   ```

4. **Implement Logic**:
   - Override `handle_custom_message()` for message handling
   - Override `main_loop()` for continuous work
   - Use `self.log_info()`, `self.send_message()` for communication

### BaseSubProcess Features

Every subprocess automatically gets:
- **Registration system** - Automatic registration with ControlPanel
- **Health monitoring** - Responds to ping/pong automatically
- **Message handling** - ZeroMQ pub/sub communication
- **Graceful shutdown** - Handles shutdown commands
- **Crash protection** - Automatic crash logging to desktop
- **Convenience methods** - `log_info()`, `log_error()`, etc.

## ⚙️ Configuration

### Port Configuration
- **Authentication**: 2828 (temporary)
- **Control Panel**: 2828 (after auth shutdown)
- **ZeroMQ Publisher**: 5555
- **ZeroMQ Subscriber**: 5556

### Health Monitoring
- **Ping interval**: 5 seconds
- **Ping timeout**: 15 seconds (process killed if no response)
- **Registration retries**: 30 attempts, 2-second intervals

### Logging
- **Crash logs**: Written to desktop with full traceback
- **Message history**: Last 1000 messages kept in memory
- **Real-time display**: Filtered messages shown in Control Panel

## 🛠️ Technical Details

### Process Isolation
- Each subprocess runs with **independent GIL**
- **Separate console windows** in development mode
- **No shared memory** - all communication via ZeroMQ
- **Independent crash domains** - one process failure doesn't affect others

### Registry System
- **Single entry point**: All subprocesses launched via `main.py --registry ProcessName`
- **Dynamic routing**: Registry maps process names to implementation folders
- **Module loading**: Uses `importlib` for clean subprocess execution

### Error Handling
- **Comprehensive crash logging** with full traceback to desktop
- **Process supervision** - ControlPanel monitors and restarts failed processes
- **Network resilience** - Subprocesses shutdown if broker unavailable
- **Graceful degradation** - System continues if non-critical processes fail

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: System automatically kills processes on required ports
2. **Subprocess not starting**: Check registry configuration and folder structure
3. **Registration failures**: Ensure ZeroMQ broker is running first
4. **UI not updating**: Check browser console for WebSocket connection errors

### Debug Information
- **Desktop crash logs**: `sunshine_crash_[component]_[timestamp].log`
- **Process console output**: Each subprocess has its own console window
- **Control Panel debug panel**: Real-time event logging in web UI
- **ZeroMQ message flow**: All messages logged in ControlPanel console

## 🏁 Production Deployment

### Building Executable
```bash
./build_prod.sh
```

This creates a single `sunshine_system.exe` that includes:
- All Python dependencies
- HTML templates bundled
- No console windows (except for debug)
- Self-contained executable

### System Requirements
- **OS**: Windows (uses Windows-specific process management)
- **Python**: 3.12+ (for development)
- **Dependencies**: Flask, Flask-SocketIO, pyzmq (auto-installed via pipenv)

## 📈 Extending the System

### Custom Message Types
```python
# Add to utils/message_types.py
MSG_CUSTOM_COMMAND = "CUSTOM_COMMAND"
MSG_CUSTOM_RESPONSE = "CUSTOM_RESPONSE"
```

### Custom Subprocess Logic
```python
class MySubprocess(BaseSubProcess):
    def handle_custom_message(self, message):
        if message.get('message_type') == 'CUSTOM_COMMAND':
            # Handle custom logic
            self.send_message('CUSTOM_RESPONSE', {'result': 'success'})
    
    def main_loop(self):
        while not self.shutdown_flag.is_set():
            # Your continuous work here
            self.log_info("Processing...")
            time.sleep(1)
```

### Integration Points
- **REST APIs**: Add Flask routes to ControlPanel
- **Database**: Add database connections to individual subprocesses  
- **External Services**: Integrate APIs within subprocess main loops
- **File Processing**: Handle file operations in dedicated subprocesses

---

## 🎯 System Benefits

- **🔧 Modular**: Easy to add/remove/modify individual components
- **🔒 Isolated**: Process failures don't cascade to other components  
- **📊 Observable**: Real-time monitoring and debugging capabilities
- **⚡ Scalable**: Add new subprocesses without affecting existing ones
- **🛡️ Resilient**: Health monitoring and automatic process management
- **🎨 User-Friendly**: Web-based dashboard for system oversight

The Sunshine System provides a robust foundation for building distributed applications with independent, communicating processes that are easy to monitor, debug, and extend.