import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

def setup_crash_handler(comet_name: str):
    """Setup exception handler that logs crashes to Documents/Sunshine/Crash."""
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        # Don't log KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Get crash directory
        if os.name == 'nt':  # Windows
            documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
        else:  # Linux/Mac
            documents = os.path.join(os.path.expanduser('~'), 'Documents')
        
        crash_dir = Path(documents) / 'Sunshine' / 'Crash'
        crash_dir.mkdir(parents=True, exist_ok=True)
        
        # Create crash file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        crash_file = crash_dir / f"{comet_name}_{timestamp}.log"
        
        # Write crash log
        with open(crash_file, 'w') as f:
            f.write(f"Comet Crash Report\n")
            f.write(f"==================\n")
            f.write(f"Comet: {comet_name}\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"\nException:\n")
            f.write(f"{exc_type.__name__}: {exc_value}\n")
            f.write(f"\nTraceback:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        print(f"💥 Crash dump saved to: {crash_file}")
        
        # Also print to console
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Set as the default exception handler
    sys.excepthook = handle_exception

def log_crash(comet_name: str, error_msg: str, exception: Exception = None):
    """Manually log a crash or error."""
    if os.name == 'nt':  # Windows
        documents = os.path.join(os.environ['USERPROFILE'], 'Documents')
    else:  # Linux/Mac
        documents = os.path.join(os.path.expanduser('~'), 'Documents')
    
    crash_dir = Path(documents) / 'Sunshine' / 'Crash'
    crash_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    crash_file = crash_dir / f"{comet_name}_{timestamp}.log"
    
    with open(crash_file, 'w') as f:
        f.write(f"Comet Error Report\n")
        f.write(f"==================\n")
        f.write(f"Comet: {comet_name}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Error: {error_msg}\n")
        if exception:
            f.write(f"\nException Details:\n")
            f.write(f"{type(exception).__name__}: {str(exception)}\n")
            f.write(f"\nTraceback:\n")
            f.write(traceback.format_exc())
