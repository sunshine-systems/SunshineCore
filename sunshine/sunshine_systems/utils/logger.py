import os
import traceback
from datetime import datetime

def crash_logger(component_name, exception):
    """Log crash information to desktop file."""
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"sunshine_crash_{component_name}_{timestamp}.log"
    log_filepath = os.path.join(desktop_path, log_filename)
    
    try:
        with open(log_filepath, 'w') as f:
            f.write(f"Sunshine System Crash Report\n")
            f.write(f"Component: {component_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Exception: {str(exception)}\n\n")
            f.write(f"Full Traceback:\n")
            f.write(traceback.format_exc())
        
        print(f"Crash log written to: {log_filepath}")
    except Exception as e:
        print(f"Failed to write crash log: {e}")
