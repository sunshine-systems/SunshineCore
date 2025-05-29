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
        # Set the subprocess name
        super().__init__("SunBoxInterface")
        
        # Custom initialization for SunBoxInterface
        self.custom_data = {}
        self.iteration_count = 0
        print(f"SunBoxInterface: Initialized with PID {os.getpid()}")
    
    def handle_custom_message(self, message):
        """Handle custom messages specific to SunBoxInterface."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Handle SunBox-specific message types
            if msg_type == 'SUNBOX_COMMAND':
                self.handle_sunbox_command(payload)
            
            elif msg_type == 'SUNBOX_STATUS':
                self.handle_sunbox_status(payload, sender)
            
            elif msg_type == MSG_LOG:
                # Process log messages from other components if needed
                log_level = payload.get('level', 'INFO')
                log_message = payload.get('message', '')
                # Uncomment to see logs from other processes:
                # print(f"SunBoxInterface: Received log [{log_level}] from {sender}: {log_message}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
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
                    print(f"SunBoxInterface: Retrieved data {key} = {self.custom_data[key]}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
            print(f"SunBoxInterface: Error handling command: {e}")
    
    def handle_sunbox_status(self, payload, sender):
        """Handle status messages from other SunBox components."""
        try:
            self.log_info(f"Received status from {sender}: {payload}")
            print(f"SunBoxInterface: Status from {sender}: {payload}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_handling", e)
            print(f"SunBoxInterface: Error handling status: {e}")
    
    def main_loop(self):
        """Main processing loop for SunBoxInterface."""
        try:
            print("SunBoxInterface: Starting main loop...")
            
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Simple demo: Hello world every 5 seconds
                hello_message = f"SunBoxInterface Hello World #{self.iteration_count}"
                self.log_info(hello_message)
                print(f"SunBoxInterface: {hello_message}")
                
                # Do SunBox-specific work
                self.do_sunbox_work()
                
                # Send periodic status updates every 10 iterations (50 seconds)
                if self.iteration_count % 10 == 0:
                    self.send_sunbox_status()
                
                # Sleep for 5 seconds between iterations
                time.sleep(5)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            print(f"SunBoxInterface: Error in main loop: {e}")
            self.shutdown()
    
    def do_sunbox_work(self):
        """SunBox-specific processing work."""
        try:
            # SunBox-specific logic here
            current_time = time.time()
            self.custom_data['last_run'] = current_time
            self.custom_data['iteration'] = self.iteration_count
            
            # Example: Monitor system, process data, etc.
            # Add your SunBox-specific functionality here
            
        except Exception as e:
            crash_logger(f"{self.process_name}_sunbox_work", e)
            print(f"SunBoxInterface: Error in SunBox work: {e}")
    
    def send_sunbox_status(self):
        """Send SunBox status update to other processes."""
        try:
            status_msg = {
                'process_name': self.process_name,
                'iteration': self.iteration_count,
                'status': 'running',
                'data_items': len(self.custom_data),
                'timestamp': time.time(),
                'sunbox_specific': {
                    'interface_version': '1.0',
                    'active_connections': 0,  # Example data
                    'processed_items': self.iteration_count
                }
            }
            
            self.send_message('SUNBOX_STATUS', status_msg)
            print(f"SunBoxInterface: Sent status update: iteration {self.iteration_count}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_update", e)
            print(f"SunBoxInterface: Error sending status update: {e}")

def main():
    try:
        print("="*50)
        print("SUNBOX INTERFACE STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        print(f"Python Path: {sys.path[:3]}...")  # Show first 3 entries
        
        # Create and start the SunBoxInterface
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
