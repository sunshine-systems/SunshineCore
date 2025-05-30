import sys
import os
import subprocess
import time
import socket
from pathlib import Path
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
        
        # Phase 3: Start registered subprocesses (Control Panel)
        print("\nPhase 3: Starting Control Panel")
        print("-" * 30)
        
        launched_count = launch_all_subprocesses(dev_mode)
        
        # Phase 4: Start plugin Comets
        print("\nPhase 4: Starting Plugin Comets")
        print("-" * 30)
        
        plugin_count = launch_plugin_comets(dev_mode)
        
        print(f"\n🚀 System startup complete:")
        print(f"   - ZeroMQ Broker (ports 5555/5556)")
        print(f"   - Control Panel (http://127.0.0.1:2828)")
        print(f"   - {launched_count} internal subprocess(es)")
        print(f"   - {plugin_count} plugin Comet(s)")
        print("\nMain process exiting in 3 seconds...")
        
        # Brief pause then exit - all processes continue running
        for i in range(3, 0, -1):
            print(f"   Exiting in {i}...")
            time.sleep(1)
        print("Main process terminated. All processes continue running. ✅")
        
    except Exception as e:
        crash_logger("main_application", e)
        print(f"\n❌ Critical error in main application: {e}")
        print("Crash dump written to desktop.")
        import traceback
        traceback.print_exc()
        return

def launch_plugin_comets(dev_mode):
    """Launch all Comets found in the user's Documents/Sunshine/plugins directory."""
    # Get user's Documents folder
    if os.name == 'nt':  # Windows
        documents_path = os.path.join(os.environ['USERPROFILE'], 'Documents')
    else:  # Linux/Mac
        documents_path = os.path.join(os.path.expanduser('~'), 'Documents')
    
    plugins_dir = os.path.join(documents_path, 'Sunshine', 'plugins')
    
    # Create plugins directory if it doesn't exist
    if not os.path.exists(plugins_dir):
        try:
            os.makedirs(plugins_dir)
            print(f"   Created plugins directory: {plugins_dir}")
        except Exception as e:
            print(f"   Failed to create plugins directory: {e}")
            return 0
    
    # Look for executables (with or without .exe extension)
    plugin_files = []
    if os.name == 'nt':
        plugin_files = list(Path(plugins_dir).glob('*.exe'))
    else:
        # On Unix, executables might not have extension
        for file in Path(plugins_dir).iterdir():
            if file.is_file() and os.access(file, os.X_OK):
                plugin_files.append(file)
    
    if not plugin_files:
        print(f"   No plugin Comets found in: {plugins_dir}")
        return 0
    
    print(f"   Found {len(plugin_files)} Comet(s) in: {plugins_dir}")
    
    launched = 0
    for plugin_file in plugin_files:
        try:
            print(f"\n🌟 Launching Comet: {plugin_file.name}")
            
            cmd = [str(plugin_file)]
            if dev_mode:
                cmd.append('--dev')
            
            if os.name == 'nt':  # Windows
                if dev_mode:
                    proc = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        cwd=plugins_dir
                    )
                else:
                    proc = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        cwd=plugins_dir
                    )
            else:  # Linux/Mac
                proc = subprocess.Popen(cmd, cwd=plugins_dir)
            
            print(f"   ✅ Launched {plugin_file.name} (PID: {proc.pid})")
            launched += 1
            
            # Small delay between launches
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Failed to launch {plugin_file.name}: {e}")
    
    return launched

def launch_all_subprocesses(dev_mode):
    """Launch all internal subprocesses."""
    launched_count = 0
    
    for i, config in enumerate(SUBPROCESS_REGISTRY):
        process_num = i + 1
        
        print(f"\n{'='*60}")
        print(f"🚀 LAUNCHING PROCESS {process_num}/{len(SUBPROCESS_REGISTRY)}: {config['name']}")
        print(f"{'='*60}")
        
        try:
            cmd = [sys.executable, 'main.py', '--registry', config['name']]
            
            if dev_mode and config.get('show_console', True):
                if os.name == 'nt':  # Windows
                    proc = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        cwd=os.getcwd()
                    )
                    print(f"   ✅ {config['name']} launched with PID: {proc.pid}")
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
            
        except Exception as e:
            print(f"❌ Failed to launch {config['name']}: {e}")
    
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
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=os.getcwd()
            )
        else:  # Linux/Mac
            subprocess.Popen(cmd, cwd=os.getcwd())
    else:
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
