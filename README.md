# SunshineCore

A distributed plugin architecture for Windows built with Python 3.12 that manages independent processes (Comets) through a ZeroMQ message broker.

## 🌟 Overview

SunshineCore is a lightweight process orchestrator that:
- Manages a constellation of independent executable plugins (Comets)
- Provides real-time monitoring through a web-based Control Panel
- Handles inter-process communication via ZeroMQ
- Ensures system health with automatic ping/pong monitoring
- Supports both development and production deployment modes

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Main Process  │    │   ZeroMQ Broker  │    │  Control Panel  │
│   (Launcher)    │    │  (Message Relay) │    │   (Web UI)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
            ┌───────────────┐           ┌───────────────┐
            │  Plugin Comet  │           │  Plugin Comet  │
            │ (From Plugins) │           │ (From Plugins) │
            └───────────────┘           └───────────────┘
```

## 🚀 Installation & Usage

### Prerequisites
- Windows OS (primary support)
- Python 3.12+
- Git Bash or similar Unix-like shell for Windows

### Development Mode

```bash
# Clone the repository
git clone <your-repo-url>
cd SunshineCore

# Run in development mode (shows console windows)
./run_dev.sh
```

### Production Build

```bash
# Build the executable
./build_prod.sh

# The executable will be created as sunshine_system.exe
```

## 📁 Directory Structure

```
SunshineCore/
├── run_dev.sh                    # Development launcher
├── build_prod.sh                 # Production build script
└── sunshine_systems/
    ├── main.py                   # Main entry point
    ├── Pipfile                   # Python dependencies
    ├── auth/                     # Authentication system
    ├── zeromq/                   # Message broker
    ├── subprocesses/
    │   └── control_panel/        # Web monitoring UI
    ├── templates/                # HTML templates
    ├── utils/                    # Utilities
    └── config/                   # Configuration
```

## 🔌 Plugin System

SunshineCore automatically loads and manages executable plugins (Comets) from:
- **Windows**: `%USERPROFILE%\Documents\Sunshine\plugins\`
- **Mac/Linux**: `~/Documents/Sunshine/plugins/`

### Installing Plugins

1. Download or build a `.exe` Comet
2. Copy it to your `Documents/Sunshine/plugins/` folder
3. Start SunshineCore - it will automatically detect and launch all plugins

### Plugin Communication

Plugins communicate using **SolarFlares** (messages) through ZeroMQ:
- **Publisher Port**: 5555
- **Subscriber Port**: 5556

## 📊 Control Panel

Access the web-based control panel at: `http://localhost:2828`

Features:
- Real-time process monitoring
- Live message stream
- Process health status
- Manual shutdown controls
- WebSocket-based updates

## 🔧 Configuration

Edit `config/settings.py` to modify:
- Port numbers
- Health check intervals
- Message history limits
- Timeout values

## 💬 Message Types

### System Messages (Handled Automatically)
- `REGISTER` / `REGISTER_ACK` - Process registration
- `PING` / `PONG` - Health monitoring
- `SHUTDOWN` / `SHUTDOWN_ACK` - Graceful shutdown
- `LOG` - System logging

### Custom Messages
Comets can define and use any custom message types for their specific needs.

## 🛠️ Creating Your Own Comet

See the [CometExample](../CometExample/README.md) project for a complete template and guide on creating your own plugins.

Basic steps:
1. Copy the CometExample template
2. Implement your logic in `main.py`
3. Build the executable
4. Drop it in the plugins folder

## 🚨 Troubleshooting

### Crash Logs
All Comet crashes are automatically logged to:
- **Windows**: `%USERPROFILE%\Documents\Sunshine\Crash\`
- **Mac/Linux**: `~/Documents/Sunshine/Crash/`

### Common Issues

1. **Port Already in Use**
   - SunshineCore uses ports 2828, 5555, and 5556
   - Ensure no other applications are using these ports

2. **Comets Not Loading**
   - Check the plugins directory exists
   - Ensure Comet files are executable
   - Check crash logs for startup errors

3. **Registration Timeout**
   - Ensure ZeroMQ broker is running
   - Check firewall settings
   - Verify network connectivity

## 🔄 System Flow

1. **Authentication Phase**
   - User authenticates via web interface
   - Browser automatically opens to auth page

2. **Broker Initialization**
   - ZeroMQ broker starts on ports 5555/5556
   - Health check confirms broker readiness

3. **Control Panel Launch**
   - Web UI starts on port 2828
   - WebSocket connection established

4. **Plugin Discovery**
   - Scans `Documents/Sunshine/plugins/`
   - Launches each executable found

5. **Runtime Management**
   - Continuous health monitoring
   - Automatic dead process cleanup
   - Graceful shutdown handling

## 📈 Development

### Adding Dependencies

```bash
cd sunshine_systems
pipenv install <package-name>
```

### Running Tests

```bash
# Add your test commands here
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🎯 Design Philosophy

- **Modularity**: Each Comet is completely independent
- **Resilience**: Process failures don't affect others
- **Observability**: Real-time monitoring of all components
- **Simplicity**: Easy to create and deploy new Comets
- **Flexibility**: Support for any executable as a plugin

## 📝 License

[Your License Here]

## 🤝 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check existing documentation
- Review crash logs in `Documents/Sunshine/Crash/`

---

Built with ❤️ using Python, ZeroMQ, Flask, and SocketIO