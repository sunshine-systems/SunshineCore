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
        print(f"Main Process PID: {os.getpid()}")
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
        
        launched_count = launch_all_subprocesses_debug(dev_mode)
        
        print(f"\n🚀 Launched {launched_count}/{len(SUBPROCESS_REGISTRY)} subprocess commands")
        print("\n" + "="*50)
        print("SUNSHINE SYSTEM STARTUP COMPLETE")
        print("="*50)
        print("\nAll subprocess launch commands have been issued:")
        print("- ZeroMQ Broker (ports 5555/5556)")
        print("- Control Panel (http://127.0.0.1:2828)")
        print(f"- {len(SUBPROCESS_REGISTRY)} subprocess(es)")
        print("\nMain process exiting in 3 seconds...")
        print("Subprocesses will continue initializing independently.")
        
        # Brief pause then exit - all subprocesses continue running
        for i in range(3, 0, -1):
            print(f"   Exiting in {i}...")
            time.sleep(1)
        print("Main process terminated. All subprocesses continue running. ✅")
        
    except Exception as e:
        crash_logger("main_application", e)
        print(f"\n❌ Critical error in main application: {e}")
        print("Crash dump written to desktop.")
        import traceback
        traceback.print_exc()
        # Don't use sys.exit, just return
        return

def launch_all_subprocesses_debug(dev_mode):
    """DEBUG VERSION - Launch all subprocesses with extensive logging."""
    print(f"🚀 DEBUG SUBPROCESS LAUNCHER")
    print(f"📋 Registry contains {len(SUBPROCESS_REGISTRY)} processes:")
    for i, config in enumerate(SUBPROCESS_REGISTRY):
        print(f"   {i+1}. {config['name']} ({config['folder']})")
    
    launched_count = 0
    
    # Launch ALL subprocesses
    for i, config in enumerate(SUBPROCESS_REGISTRY):
        process_num = i + 1
        
        print(f"\n{'='*60}")
        print(f"🚀 LAUNCHING PROCESS {process_num}/{len(SUBPROCESS_REGISTRY)}: {config['name']}")
        print(f"{'='*60}")
        
        try:
            cmd = [sys.executable, 'main.py', '--registry', config['name']]
            print(f"📋 Command: {' '.join(cmd)}")
            print(f"📁 Working Dir: {os.getcwd()}")
            print(f"🖥️  Show Console: {config.get('show_console', True)}")
            
            if dev_mode and config.get('show_console', True):
                if os.name == 'nt':  # Windows
                    print(f"🪟 Creating Windows console window...")
                    # Store process reference to check if it started
                    proc = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        cwd=os.getcwd()
                    )
                    print(f"   ✅ {config['name']} launched with PID: {proc.pid}")
                    
                    # Brief check to see if process is still alive
                    time.sleep(0.2)
                    if proc.poll() is not None:
                        print(f"   ⚠️  Process exited immediately with code: {proc.returncode}")
                    else:
                        print(f"   ✅ Process still running after 0.2s")
                else:  # Linux/Mac
                    proc = subprocess.Popen(cmd, cwd=os.getcwd())
                    print(f"   ✅ {config['name']} launched")
            else:
                if os.name == 'nt':  # Windows
                    proc = subprocess.Popen(
                        cmd,
                        cwd=os.getcwd(),
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:  # Linux/Mac
                    proc = subprocess.Popen(cmd, cwd=os.getcwd())
                print(f"   ✅ {config['name']} background launched")
            
            launched_count += 1
            print(f"✅ Successfully launched {config['name']}")
            
            # Small delay between launches
            if process_num < len(SUBPROCESS_REGISTRY):
                print(f"⏳ Waiting 0.5s before next process...")
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Failed to launch {config['name']}: {e}")
            import traceback
            traceback.print_exc()
            # Continue launching others
    
    print(f"\n{'='*60}")
    print(f"🏁 All launch attempts completed!")
    print(f"✅ Successfully launched: {launched_count}/{len(SUBPROCESS_REGISTRY)}")
    print(f"{'='*60}")
    
    return launched_count

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
            
            import importlib.util
            
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
        import traceback
        traceback.print_exc()
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
        if os.name == 'nt':  # Windows
            # Use CREATE_NEW_CONSOLE only for visible console
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()
            )
        else:  # Linux/Mac
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
                subprocess.Popen(cmd, cwd=os.getcwd())
    else:
        if os.name == 'nt':  # Windows
            # Use CREATE_NO_WINDOW for background process
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

if __name__ == "__main__":
    main()
