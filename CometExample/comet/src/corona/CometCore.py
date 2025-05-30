import sys
import os
import time
import threading
from queue import Queue
from datetime import datetime
from .SolarFlare import SolarFlare
from .Satellite import Satellite
from .crash_handler import setup_crash_handler, log_crash

class CometCore:
    """Core functionality for all Comets."""
    
    # System message types
    MSG_REGISTER = "REGISTER"
    MSG_REGISTER_ACK = "REGISTER_ACK"
    MSG_PING = "PING"
    MSG_PONG = "PONG"
    MSG_SHUTDOWN = "SHUTDOWN"
    MSG_SHUTDOWN_ACK = "SHUTDOWN_ACK"
    
    def __init__(self, name: str, subscribe_to: list, in_queue: Queue, out_queue: Queue,
                 on_startup=None, on_shutdown=None, main_loop=None):
        self.name = name
        self.pid = os.getpid()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.system_queue = Queue()  # For system messages
        self.subscribe_to = subscribe_to
        self.on_startup = on_startup
        self.on_shutdown = on_shutdown
        self.main_loop = main_loop
        self.registered = False
        self.running = True
        self.shutdown_event = threading.Event()  # For main loop to check
        self.last_ping_time = time.time()
        self.dev_mode = "--dev" in sys.argv
        
        # Setup crash handler
        setup_crash_handler(self.name)
        
        # Hide console in production mode
        if not self.dev_mode and os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0
                )
            except:
                pass
        
        # All system messages we need to see
        system_messages = [
            self.MSG_REGISTER_ACK,
            self.MSG_PING,
            self.MSG_SHUTDOWN
        ]
        
        # Combine user filters with system messages
        all_filters = list(set(subscribe_to + system_messages))
        
        # Initialize satellite
        self.satellite = Satellite(
            self.name,
            self.system_queue,
            self.out_queue,
            all_filters if "*" not in subscribe_to else ["*"]
        )
    
    def start(self):
        """Start the Comet."""
        try:
            print(f"🌟 {self.name} starting (PID: {self.pid})")
            
            # Connect to ZeroMQ
            self.satellite.connect()
            self.satellite.start()
            
            # Start system message handler
            system_thread = threading.Thread(target=self._handle_system_messages, daemon=True)
            system_thread.start()
            
            # Call startup hook
            if self.on_startup:
                self.on_startup()
            
            # Register with ControlPanel
            if not self._register():
                print(f"❌ {self.name} failed to register")
                log_crash(self.name, "Failed to register with ControlPanel")
                self._shutdown()
                return
            
            print(f"✅ {self.name} registered successfully")
            
            # Start health monitor
            health_thread = threading.Thread(target=self._monitor_health, daemon=True)
            health_thread.start()
            
            # Run main loop
            if self.main_loop:
                # Pass a function to check if still running
                self.main_loop(lambda: not self.shutdown_event.is_set())
            else:
                # Default main loop
                while not self.shutdown_event.is_set():
                    time.sleep(1)
            
            # If we get here, main loop has exited cleanly
            if not self.shutdown_event.is_set():
                print(f"🔄 {self.name} main loop completed")
                self._shutdown()
                    
        except Exception as e:
            print(f"❌ {self.name} error: {e}")
            log_crash(self.name, f"Fatal error during startup: {e}", e)
            if not self.shutdown_event.is_set():
                self._shutdown()
        
        # If we get here, main loop has exited
        print(f"🔄 {self.name} main loop completed, shutting down...")
        self._shutdown()
    
    def _register(self):
        """Register with ControlPanel."""
        max_attempts = 30
        
        for attempt in range(max_attempts):
            # Send registration
            reg_flare = SolarFlare(
                timestamp=datetime.now(),
                name=self.name,
                type=self.MSG_REGISTER,
                payload={'process_name': self.name, 'process_id': self.pid}
            )
            self.out_queue.put(reg_flare)
            
            # Wait for ACK
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.registered:
                    return True
                time.sleep(0.1)
            
            print(f"{self.name}: Registration attempt {attempt + 1}/{max_attempts}")
        
        return False
    
    def _handle_system_messages(self):
        """Handle system messages separately from user messages."""
        while not self.shutdown_event.is_set():
            try:
                if not self.system_queue.empty():
                    flare = self.system_queue.get()
                    
                    # Route to user queue if it's a subscribed message
                    if flare.type in self.subscribe_to or "*" in self.subscribe_to:
                        self.in_queue.put(flare)
                    
                    # Handle system messages
                    if flare.type == self.MSG_REGISTER_ACK:
                        if flare.payload.get('process_name') == self.name:
                            self.registered = True
                    
                    elif flare.type == self.MSG_PING:
                        if flare.name == 'ControlPanel':
                            self.last_ping_time = time.time()
                            pong = SolarFlare(
                                timestamp=datetime.now(),
                                name=self.name,
                                type=self.MSG_PONG,
                                payload={
                                    'process_name': self.name,
                                    'process_id': self.pid,
                                    'timestamp': time.time()
                                }
                            )
                            self.out_queue.put(pong)
                    
                    elif flare.type == self.MSG_SHUTDOWN:
                        target = flare.payload.get('target')
                        if target == '*' or target == self.name:
                            # Send ACK
                            ack = SolarFlare(
                                timestamp=datetime.now(),
                                name=self.name,
                                type=self.MSG_SHUTDOWN_ACK,
                                payload={
                                    'process_name': self.name,
                                    'process_id': self.pid,
                                    'shutdown_target': target,
                                    'timestamp': time.time()
                                }
                            )
                            self.out_queue.put(ack)
                            print(f"{self.name}: Shutdown ACK sent")
                            time.sleep(0.5)
                            self._shutdown()
                
                time.sleep(0.01)
                
            except Exception as e:
                error_msg = f"{self.name} system message error: {e}"
                print(error_msg)
                log_crash(self.name, error_msg, e)
    
    def _monitor_health(self):
        """Monitor connection health."""
        while not self.shutdown_event.is_set():
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:
                    error_msg = f"No ping for {int(time_since_ping)}s, shutting down"
                    print(f"⚠️ {self.name}: {error_msg}")
                    log_crash(self.name, error_msg)
                    self._shutdown()
                    break
            time.sleep(1)
    
    def _shutdown(self):
        """Shutdown the Comet."""
        # Prevent multiple shutdown calls
        if self.shutdown_event.is_set():
            return
            
        print(f"🛑 {self.name} shutting down...")
        self.running = False
        self.shutdown_event.set()  # Signal main loop to stop
        
        # Give main loop a moment to finish
        time.sleep(0.1)
        
        if self.on_shutdown:
            try:
                self.on_shutdown()
            except Exception as e:
                log_crash(self.name, f"Error in shutdown hook: {e}", e)
        
        self.satellite.shutdown()
        time.sleep(0.5)
        sys.exit(0)
