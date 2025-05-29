import sys
import os
import subprocess
import time
import socket
from auth.startup import start_auth_server
from subprocesses.registry import SUBPROCESS_REGISTRY, get_subprocess_folder_by_name
from utils.logger import crash_logger
from config.settings import *

def main():
    # Check if this is a subprocess call
    if '--registry' in sys.argv:
        registry_name = sys.argv[sys.argv.index('--registry') + 1]
        print(f"Starting subprocess: {registry_name}")
        run_subprocess(registry_name)
        return

    # Main startup process
    try:
        # Check for dev mode
        dev_mode = '--devmode' in sys.argv
        
        print("="*50)
        print("SUNSHINE SYSTEM STARTUP")
        print("="*50)
        
        # Phase 1: Authentication (BLOCKING)
        print("\nPhase 1: Authentication")
        print("-" * 25)
        auth_success = start_auth_server()
        
        if not auth_success:
            print("\n❌ Authentication failed or timed out. System will NOT start.")
            print("Please try again.")
            return
        
        # Phase 2: Start ZeroMQ Broker as subprocess
        print("\nPhase 2: Starting ZeroMQ Broker")
        print("-" * 35)
        try:
            start_zeromq_broker_subprocess(dev_mode)
            print("✅ ZeroMQ Broker subprocess started")
            
            # Wait for broker to be ready
            print("   Waiting for broker to initialize...")
            if wait_for_broker_ready():
                print("✅ ZeroMQ Broker is ready")
            else:
                print("❌ ZeroMQ Broker failed to initialize")
                return
                
        except Exception as e:
            print(f"❌ Failed to start ZeroMQ Broker: {e}")
            crash_logger("zeromq_broker_startup", e)
            return
        
        # Phase 3: Start registered subprocesses
        print("\nPhase 3: Starting Subprocesses")
        print("-" * 30)
        print(f"About to start {len(SUBPROCESS_REGISTRY)} subprocesses...")
        
        print("DEBUG: About to call start_subprocesses function...")
        success_count = start_subprocesses(dev_mode)
        print(f"DEBUG: start_subprocesses returned with success_count: {success_count}")
        
        print(f"\n✅ Started {success_count}/{len(SUBPROCESS_REGISTRY)} subprocesses")
        print("\n" + "="*50)
        print("SUNSHINE SYSTEM STARTUP COMPLETE")
        print("="*50)
        print("\nAll systems are now running independently:")
        print("- ZeroMQ Broker (ports 5555/5556)")
        print("- Control Panel (http://127.0.0.1:2828)")
        print(f"- {len(SUBPROCESS_REGISTRY)} subprocess(es)")
        print("\nMain process exiting in 3 seconds...")
        
        # Brief pause then exit - all subprocesses continue running
        for i in range(3, 0, -1):
            print(f"   Exiting in {i}...")
            time.sleep(1)
        print("Main process terminated. All subprocesses continue running. ✅")
        
    except Exception as e:
        crash_logger("main_application", e)
        print(f"\n❌ Critical error in main application: {e}")
        print("Crash dump written to desktop.")
        sys.exit(1)

def run_subprocess(registry_name):
    """Run a specific subprocess by executing its main.py file directly."""
    try:
        subprocess_folder = get_subprocess_folder_by_name(registry_name)
        if subprocess_folder:
            subprocess_path = os.path.join('subprocesses', subprocess_folder, 'main.py')
            
            if not os.path.exists(subprocess_path):
                print(f"❌ Subprocess main.py not found: {subprocess_path}")
                sys.exit(1)
            
            print(f"Executing subprocess: {subprocess_path}")
            print(f"Working directory: {os.getcwd()}")
            
            # Instead of exec, we'll run python directly on the subprocess file
            # But since we're already in a subprocess call, we need to import and run directly
            import importlib.util
            import importlib
            
            # Add the subprocess directory to Python path
            subprocess_dir = os.path.join(os.getcwd(), 'subprocesses', subprocess_folder)
            if subprocess_dir not in sys.path:
                sys.path.insert(0, subprocess_dir)
            
            # Add parent directory for imports
            parent_dir = os.path.join(os.getcwd())
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Load and execute the module
            spec = importlib.util.spec_from_file_location("subprocess_main", subprocess_path)
            module = importlib.util.module_from_spec(spec)
            
            # Set up the module's __file__ attribute
            module.__file__ = subprocess_path
            
            # Execute the module
            spec.loader.exec_module(module)
            
            # Call main if it exists
            if hasattr(module, 'main'):
                module.main()
            
        else:
            print(f"❌ Unknown subprocess: {registry_name}")
            sys.exit(1)
    except Exception as e:
        crash_logger(f"subprocess_{registry_name}", e)
        print(f"❌ Fatal error in {registry_name}: {e}")
        print("Press Enter to close this window...")
        try:
            input()
        except:
            time.sleep(30)
        sys.exit(1)

def start_zeromq_broker_subprocess(dev_mode):
    """Start ZeroMQ broker as an independent subprocess."""
    broker_path = os.path.join('zeromq', 'broker.py')
    
    if not os.path.exists(broker_path):
        raise FileNotFoundError(f"ZeroMQ broker not found: {broker_path}")
    
    cmd = [sys.executable, broker_path]
    
    if dev_mode:
        # Start with console window in dev mode
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()
            )
        else:  # Linux/Mac - use terminal emulator
            try:
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'x-terminal-emulator']
                for terminal in terminals:
                    try:
                        if terminal == 'gnome-terminal':
                            subprocess.Popen([terminal, '--', *cmd], cwd=os.getcwd())
                        else:
                            subprocess.Popen([terminal, '-e'] + cmd, cwd=os.getcwd())
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback to background process
                    print("   (Running ZeroMQ Broker in background - no terminal emulator found)")
                    subprocess.Popen(cmd, cwd=os.getcwd())
            except Exception:
                subprocess.Popen(cmd, cwd=os.getcwd())
    else:
        # Background process for production
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                cmd,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:  # Linux/Mac
            subprocess.Popen(cmd, cwd=os.getcwd())

def wait_for_broker_ready(timeout=10):
    """Wait for ZeroMQ broker to be ready by checking if ports are listening."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if broker ports are listening
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            result1 = sock1.connect_ex(('127.0.0.1', ZEROMQ_PORT))
            result2 = sock2.connect_ex(('127.0.0.1', ZEROMQ_PORT + 1))
            
            sock1.close()
            sock2.close()
            
            if result1 == 0 and result2 == 0:
                return True
                
        except Exception:
            pass
        
        time.sleep(0.5)
    
    return False

def start_subprocesses(dev_mode):
    """Start all registered subprocesses and return success count - ROBUST VERSION."""
    print("="*60)
    print("ENTERING SUBPROCESS STARTUP FUNCTION")
    print("="*60)
    
    success_count = 0
    total_processes = len(SUBPROCESS_REGISTRY)
    
    print(f"   Found {total_processes} processes in registry")
    print(f"   SUBPROCESS_REGISTRY contents: {SUBPROCESS_REGISTRY}")
    
    print(f"   Starting enumeration loop...")
    
    # Use a traditional for loop with explicit indexing to avoid any iterator issues
    for i in range(total_processes):
        subprocess_config = SUBPROCESS_REGISTRY[i]
        iteration_num = i + 1
        
        print(f"="*40)
        print(f"LOOP ITERATION {iteration_num} OF {total_processes}")
        print(f"="*40)
        
        try:
            print(f"   Processing subprocess config: {subprocess_config}")
            print(f"  {iteration_num}. Starting {subprocess_config['name']} (folder: {subprocess_config['folder']})...")
            
            print(f"     About to call start_subprocess_with_registry...")
            start_subprocess_with_registry(subprocess_config, dev_mode)
            print(f"     Returned from start_subprocess_with_registry successfully")
            
            print(f"     ✅ {subprocess_config['name']} started")
            success_count += 1
            
            print(f"     Current success_count: {success_count}")
            print(f"     Loop position: {iteration_num} of {total_processes}")
            
            if iteration_num < total_processes:  # Don't sleep after the last process
                print(f"     Sleeping 1 second before next subprocess...")
                time.sleep(1)  # Stagger startup
                print(f"     Finished sleeping, continuing to next iteration...")
            else:
                print(f"     This was the last subprocess, no sleep needed")
                
        except Exception as e:
            print(f"     ❌ EXCEPTION in subprocess loop iteration {iteration_num}")
            print(f"     Exception type: {type(e).__name__}")
            print(f"     Exception message: {str(e)}")
            print(f"     Failed to start {subprocess_config['name']}: {e}")
            crash_logger(f"subprocess_startup_{subprocess_config['name']}", e)
            # Continue with other processes
            print(f"     Continuing with remaining processes...")
            
        print(f"   COMPLETED ITERATION {iteration_num}")
    
    print(f"="*60)
    print(f"FOR LOOP COMPLETED - processed {total_processes} iterations")
    print(f"SUCCESS COUNT: {success_count}")
    print(f"="*60)
    
    print(f"   Subprocess startup loop completed. Success count: {success_count}")
    return success_count

def start_subprocess_with_registry(config, dev_mode):
    """Start a subprocess using the registry approach."""
    print(f"         ENTERING start_subprocess_with_registry for {config['name']}")
    
    cmd = [sys.executable, 'main.py', '--registry', config['name']]
    
    print(f"     Command: {' '.join(cmd)}")
    
    try:
        if dev_mode and config.get('show_console', True):
            # Windows-specific console window creation
            if os.name == 'nt':  # Windows
                print(f"         Creating Windows console subprocess...")
                process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=os.getcwd()
                )
                print(f"     Started with PID: {process.pid}")
            else:  # Linux/Mac - use terminal emulator
                print(f"         Creating Linux/Mac terminal subprocess...")
                try:
                    # Try different terminal emulators
                    terminals = ['gnome-terminal', 'xterm', 'konsole', 'x-terminal-emulator']
                    for terminal in terminals:
                        try:
                            if terminal == 'gnome-terminal':
                                process = subprocess.Popen([terminal, '--', *cmd], cwd=os.getcwd())
                            else:
                                process = subprocess.Popen([terminal, '-e'] + cmd, cwd=os.getcwd())
                            print(f"     Started with terminal {terminal}, PID: {process.pid}")
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        # Fallback to background process with output
                        print(f"     (Running {config['name']} in background - no terminal emulator found)")
                        process = subprocess.Popen(cmd, cwd=os.getcwd())
                        print(f"     Started in background, PID: {process.pid}")
                except Exception as e:
                    print(f"     Terminal launch failed, using background: {e}")
                    process = subprocess.Popen(cmd, cwd=os.getcwd())
                    print(f"     Started in background, PID: {process.pid}")
        else:
            # Background process
            print(f"         Creating background subprocess...")
            if os.name == 'nt':  # Windows
                process = subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:  # Linux/Mac
                process = subprocess.Popen(cmd, cwd=os.getcwd())
            print(f"     Started in background, PID: {process.pid}")
            
        print(f"         SUCCESSFULLY EXITING start_subprocess_with_registry for {config['name']}")
        
    except Exception as e:
        print(f"         EXCEPTION in start_subprocess_with_registry: {e}")
        raise

if __name__ == "__main__":
    main()
