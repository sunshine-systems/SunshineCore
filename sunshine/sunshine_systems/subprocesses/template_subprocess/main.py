import sys
import os
# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

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
            
            # Example: Log all received messages for debugging
            self.log_debug(f"Received {msg_type} from {sender}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
    
    def handle_custom_command(self, payload):
        """Handle custom command messages."""
        try:
            command = payload.get('command')
            data = payload.get('data', {})
            
            # Add your command handling logic here
            if command == 'example_command':
                self.log_info(f"Received example command with data: {data}")
                
                # Example: Send response back
                self.send_message('CUSTOM_RESPONSE', {
                    'command': command,
                    'result': 'success',
                    'processed_data': data
                })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_command_handling", e)
    
    def handle_another_message(self, payload, sender):
        """Handle another type of message."""
        try:
            # Add your message handling logic here
            self.log_info(f"Handling another message from {sender}: {payload}")
            
        except Exception as e:
            crash_logger(f"{self.process_name}_another_message_handling", e)
    
    def main_loop(self):
        """Main processing loop for this subprocess."""
        try:
            while not self.shutdown_flag.is_set():
                self.iteration_count += 1
                
                # Add your main processing logic here
                self.do_main_work()
                
                # Send periodic status updates
                if self.iteration_count % 10 == 0:
                    self.send_status_update()
                
                # Log heartbeat every 5 iterations
                if self.iteration_count % 5 == 0:
                    self.log_info(f"Template subprocess heartbeat #{self.iteration_count}")
                
                # Sleep between iterations
                time.sleep(5)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
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
    
    def send_status_update(self):
        """Send status update to other processes."""
        try:
            self.send_message('STATUS_UPDATE', {
                'process_name': self.process_name,
                'iteration': self.iteration_count,
                'status': 'running',
                'data_items': len(self.custom_data),
                'timestamp': time.time()
            })
            
        except Exception as e:
            crash_logger(f"{self.process_name}_status_update", e)

def main():
    try:
        # Create and start the subprocess
        subprocess = TemplateSubprocess()
        subprocess.start()
    except Exception as e:
        crash_logger("template_subprocess", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
