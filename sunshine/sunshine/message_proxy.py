#!/usr/bin/env python3
"""ZeroMQ Message Proxy"""
import os
import sys
import zmq
import signal

# Set terminal title
if sys.platform == "win32":
    os.system("title Sunshine - Message Proxy")

def main():
    print("=" * 50)
    print("🚀 SUNSHINE MESSAGE PROXY")
    print("=" * 50)
    print("Routes messages between all processes")
    print("Ports: 5555 (SUB) and 5556 (PUB)")
    print("Press Ctrl+C to shutdown")
    print("=" * 50)
    
    context = zmq.Context()
    
    # XSUB socket - publishers connect here
    xsub = context.socket(zmq.XSUB)
    xsub.bind("tcp://*:5556")
    
    # XPUB socket - subscribers connect here  
    xpub = context.socket(zmq.XPUB)
    xpub.bind("tcp://*:5555")
    
    print("\n✅ Message proxy running...")
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down proxy...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        zmq.proxy(xsub, xpub)
    except:
        pass
    finally:
        xsub.close()
        xpub.close()
        context.term()

if __name__ == "__main__":
    main()
