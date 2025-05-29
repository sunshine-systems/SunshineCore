#!/usr/bin/env python3
import os
import sys

# Add sunshine directory to Python path
sunshine_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, sunshine_dir)

# Change to sunshine directory
os.chdir(sunshine_dir)

# Set terminal title
if sys.platform == "win32":
    os.system("title Sunshine - Control Panel")

try:
    # Import and run
    from subprocesses.control_panel.control_panel import ControlPanel
    
    print("=" * 50)
    print("🎮 SUNSHINE CONTROL PANEL")
    print("=" * 50)
    print("Web UI: http://localhost:5001")
    print("Press Ctrl+C to shutdown")
    print("=" * 50)
    print()
    
    panel = ControlPanel()
    panel.run()
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nPress Enter to exit...")
    input()
    sys.exit(1)
