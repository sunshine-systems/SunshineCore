import sys
import os

# Add parent directories to path for imports - handle both exec and direct execution
current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.path.dirname(os.path.abspath(sys.argv[0]))
parent_dir = os.path.join(current_dir, '..', '..')
parent_dir = os.path.abspath(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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
        print(f"Python Path: {sys.path[:3]}...")  # Show first 3 entries
        
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
