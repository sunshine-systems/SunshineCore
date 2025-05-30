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
