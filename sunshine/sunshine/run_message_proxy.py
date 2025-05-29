#!/usr/bin/env python3
import os
import sys
import subprocess

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Change to correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set terminal title
if sys.platform == "win32":
    os.system("title Sunshine - Message Proxy")

try:
    # Import and run
    from message_proxy import main
    main()
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nPress Enter to exit...")
    input()
    sys.exit(1)
