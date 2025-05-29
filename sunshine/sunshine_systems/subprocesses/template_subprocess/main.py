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

class TemplateSubprocess(BaseSubProcess):
    def __init__(self):
        # CHANGE THIS: Set your subprocess name here
        super().__init__("TemplateSubprocess")
        
        # Add your custom initialization here
        self.custom_data = {}
        self.iteration_count = 0
        print(f"TemplateSubprocess: Initialized with PID {os.getpid()}")
    
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
            
            elif msg_type == MSG_LOG:
                # Process log messages from other components if needed
                log_level = payload.get('level', 'INFO')
                log_message = payload.get('message', '')
                # Uncomment to see logs from other processes:
                # print(f"TemplateSubprocess: Received log [{log_level}] from {sender}: {log_message}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
            print(f"TemplateSubprocess: Error handling message: {e}")
    
    def handle_custom_command(self, payload):
        """Handle custom command messages."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            # Add your command handling logic here
            if command == 'example_command':
                self.log_info(f"Received example command with data: {data}")
                print(f"TemplateSubprocess: Processed example command: {data}")
                
                # Example: Send response back
                self.send_message('CUSTOM_RESPONSE', {
                    'command': command,
                    'result': 'success',
                    'processed_data': data
                })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
            print(f"TemplateSubprocess: Error handling command: {e}")
    
    def handle_another_message(self, payload, sender):
        """Handle another type of message."""
        try:
            # Add your message handling logic here
            self.log_info(f"Handling message from {sender}: {payload}")
            print(f"TemplateSubprocess: Processed message from {sender}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_another_message_handling", e)
            print(f"TemplateSubprocess: Error handling another message: {e}")
    
    def main_loop(self):
        """Main processing loop for this subprocess."""
        try:
            print("TemplateSubprocess: Starting main loop...")
            
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Simple demo: Hello world every 5 seconds
                hello_message = f"TemplateSubprocess Hello World #{self.iteration_count}"
                self.log_info(hello_message)
                print(f"TemplateSubprocess: {hello_message}")
                
                # Add your main processing logic here
                self.do_main_work()
                
                # Send periodic status updates every 10 iterations (50 seconds)
                if self.iteration_count % 10 == 0:
                    self.send_status_update()
                
                # Sleep for 5 seconds between iterations
                time.sleep(5)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            print(f"TemplateSubprocess: Error in main loop: {e}")
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
            print(f"TemplateSubprocess: Error in main work: {e}")
    
    def send_status_update(self):
        """Send status update to other processes."""
        try:
            status_msg = {
                'process_name': self.process_name,
                'iteration': self.iteration_count,
                'status': 'running',
                'data_items': len(self.custom_data),
                'timestamp': time.time()
            }
            
            self.send_message('STATUS_UPDATE', status_msg)
            print(f"TemplateSubprocess: Sent status update: {status_msg}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_update", e)
            print(f"TemplateSubprocess: Error sending status update: {e}")

def main():
    try:
        print("="*50)
        print("TEMPLATE SUBPROCESS STARTING")
        print("="*50)
        print(f"Process ID: {os.getpid()}")
        print(f"Working Directory: {os.getcwd()}")
        print(f"Python Path: {sys.path[:3]}...")  # Show first 3 entries
        
        # Create and start the subprocess
        subprocess = TemplateSubprocess()
        print("TemplateSubprocess: Created successfully, starting...")
        subprocess.start()
    except Exception as e:
        crash_logger("template_subprocess", e)
        print(f"TemplateSubprocess: Fatal error: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

if __name__ == "__main__":
    main()
