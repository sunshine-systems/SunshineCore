#!/bin/bash
echo "🛑 Shutting down Sunshine..."

# Send shutdown command first
python << 'PYEOF'
import zmq
import json
from datetime import datetime, timezone

try:
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.connect("tcp://localhost:5556")
    
    import time
    time.sleep(0.5)
    
    message = {
        "id": "shutdown-script",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "shutdown_script",
        "topic": "control.shutdown",
        "payload": {"target": "*", "reason": "Shutdown script"}
    }
    
    msg_string = f"control.shutdown {json.dumps(message)}"
    publisher.send_string(msg_string)
    print("✅ Shutdown command sent")
    
    publisher.close()
    context.term()
except Exception as e:
    print(f"⚠️  Could not send shutdown command: {e}")
PYEOF

sleep 2

# Kill processes
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    tasklist | grep -E "(message_proxy|control_panel|test_subprocess)" | awk '{print $2}' | while read pid; do
        echo "  Killing PID $pid"
        taskkill //PID $pid //F 2>/dev/null
    done
else
    ps aux | grep -E "(message_proxy|control_panel|test_subprocess)" | grep -v grep | awk '{print $2}' | while read pid; do
        echo "  Killing PID $pid"
        kill -9 $pid 2>/dev/null
    done
fi

echo "✅ Shutdown complete"
