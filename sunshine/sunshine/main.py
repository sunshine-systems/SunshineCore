#!/usr/bin/env python3
"""Launcher with auth - starts everything in separate terminals then exits"""
import os
import sys
import time
import subprocess
from pathlib import Path

def start_process_in_new_terminal(name, script_name):
    """Start a process in its own terminal window using wrapper script"""
    print(f"🚀 Starting {name} in new terminal...")
    
    # Use the wrapper script which handles paths correctly
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)]
    
    if sys.platform == "win32":
        # Windows: Create new console window
        # Add explicit window title
        subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(Path(__file__).parent)  # Set working directory
        )
    elif sys.platform == "darwin":
        # macOS: Use Terminal.app
        script_dir = Path(__file__).parent
        apple_script = f'''
        tell application "Terminal"
            do script "cd '{script_dir}' && {' '.join(cmd)}"
        end tell
        '''
        subprocess.Popen(["osascript", "-e", apple_script])
    else:
        # Linux: Try various terminal emulators
        script_dir = Path(__file__).parent
        terminals = [
            ["gnome-terminal", "--working-directory", str(script_dir), "--", *cmd],
            ["konsole", "--workdir", str(script_dir), "-e", *cmd],
            ["xterm", "-e", f"cd '{script_dir}' && {' '.join(cmd)}"],
            ["x-terminal-emulator", "-e", f"cd '{script_dir}' && {' '.join(cmd)}"]
        ]
        
        for terminal_cmd in terminals:
            try:
                subprocess.Popen(terminal_cmd)
                break
            except FileNotFoundError:
                continue
        else:
            # Fallback: run without terminal but with correct directory
            print(f"⚠️  No terminal found, running {name} in background")
            subprocess.Popen(cmd, cwd=str(script_dir))

def main():
    print("=" * 50)
    print("🌞 MINIMAL SUNSHINE SYSTEM LAUNCHER")
    print("=" * 50)
    
    # Start message proxy in new terminal
    print("\n1️⃣ Starting message proxy...")
    start_process_in_new_terminal("message_proxy", "run_message_proxy.py")
    time.sleep(1)
    
    # Start authentication (wait for completion)
    print("2️⃣ Starting authentication...")
    auth_path = Path(__file__).parent / "auth" / "auth_system.py"
    auth_process = subprocess.Popen([sys.executable, str(auth_path)])
    auth_process.wait()  # Wait for auth to complete
    
    if auth_process.returncode != 0:
        print("❌ Authentication failed or cancelled")
        return 1
    
    # Start control panel in new terminal
    print("3️⃣ Starting control panel...")
    start_process_in_new_terminal("control_panel", "run_control_panel.py")
    time.sleep(2)  # Give control panel time to start
    
    # Start test subprocess in new terminal
    print("4️⃣ Starting test subprocess...")
    start_process_in_new_terminal("test_subprocess", "run_test_subprocess.py")
    
    print("\n✅ All processes started in separate terminals!")
    print("🌐 Control Panel UI: http://localhost:5001")
    print("💡 Use ./shutdown.sh to stop all processes")
    print("\n⚠️  Main launcher is now exiting...")
    print("    All processes continue running independently")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
