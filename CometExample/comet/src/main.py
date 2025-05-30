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

def main_loop(is_running):
    """Main processing loop."""
    global iteration_count
    
    print("🔄 CometExample main loop started")
    
    while is_running():
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
    
    print("🔄 CometExample main loop ended")

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
    # Note: main_loop receives an is_running function parameter
    # Always use while is_running(): in your main loop!
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
