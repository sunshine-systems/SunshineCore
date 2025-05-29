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
    os.system("title Sunshine - Test Subprocess")

try:
    # Import and run
    from subprocesses.test_subprocess.test_subprocess import TestSubprocess
    
    print("=" * 50)
    print("🧪 SUNSHINE TEST SUBPROCESS")
    print("=" * 50)
    print("Registers with control panel and responds to heartbeats")
    print("Press Ctrl+C to shutdown")
    print("=" * 50)
    print()
    
    subprocess = TestSubprocess()
    subprocess.run()
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nPress Enter to exit...")
    input()
    sys.exit(1)
