import subprocess
import time

def kill_process_on_port(port):
    """Kill any process using the specified port (Windows-specific)."""
    try:
        # Find process using the port
        result = subprocess.run(
            ['netstat', '-ano'], 
            capture_output=True, 
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                        print(f"Killed process {pid} on port {port}")
                        time.sleep(1)  # Allow port to be released
                    except subprocess.CalledProcessError:
                        print(f"Failed to kill process {pid}")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
