import sys
import os

# Add parent directories to path for imports
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
            
            elif msg_type == MSG_LOG and sender != self.process_name:
                # Optionally show logs from other processes
                log_level = payload.get('level', 'INFO')
                log_message = payload.get('message', '')
                print(f"SunBoxInterface: 📋 [{log_level}] from {sender}: {log_message}")
                
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
                    print(f"SunBoxInterface: 💾 Stored data {key} = {value}")
            
            elif command == 'get_data':
                key = data.get('key')
                if key in self.custom_data:
                    self.send_message('SUNBOX_RESPONSE', {
                        'command': 'get_data',
                        'key': key,
                        'value': self.custom_data[key]
                    })
                    print(f"SunBoxInterface: 📤 Sent data {key} = {self.custom_data[key]}")
                    
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
            print(f"SunBoxInterface: Error handling command: {e}")
    
    def handle_sunbox_status(self, payload, sender):
        """Handle status messages from other SunBox components."""
        try:
            print(f"SunBoxInterface: 📊 Status from {sender}: {payload}")
        except Exception as e:
            crash_logger(f"{self.process_name}_status_handling", e)
            print(f"SunBoxInterface: Error handling status: {e}")
    
    def main_loop(self):
        """Main processing loop for SunBoxInterface."""
        try:
            print("SunBoxInterface: 🟢 Main loop started")
            
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Log activity every 20 seconds
                if self.iteration_count % 4 == 0:  # Every 4 iterations = 20 seconds
                    self.log_info(f"SunBoxInterface iteration #{self.iteration_count}")
                    print(f"\nSunBoxInterface: 🔄 Iteration #{self.iteration_count}")
                
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
            
            # Simulate some work
            if self.iteration_count % 5 == 0:
                print(f"SunBoxInterface: 💼 Processing SunBox data...")
                
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
                    'active_connections': 0,
                    'processed_items': self.iteration_count
                }
            }
            
            self.send_message('SUNBOX_STATUS', status_msg)
            print(f"SunBoxInterface: 📊 Sent status update")
            
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
        
        sunbox_interface = SunBoxInterface()
        sunbox_interface.start()
    except Exception as e:
        crash_logger("sunbox_interface", e)
        print(f"SunBoxInterface: Fatal error: {e}")
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
