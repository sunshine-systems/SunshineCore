from flask import Flask, render_template, request, jsonify
import threading
import time
import webbrowser
import os
from utils.process_manager import kill_process_on_port
from config.settings import AUTH_PORT

app = Flask(__name__, template_folder='../templates')

# Global flag to track authentication status
auth_completed = threading.Event()
flask_server = None

def start_auth_server():
    """Start authentication server and wait for user authentication."""
    # Kill any existing process on the port
    kill_process_on_port(AUTH_PORT)
    
    print("Starting authentication server...")
    
    # Start Flask server in thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(2)
    
    # Open browser automatically
    auth_url = f'http://127.0.0.1:{AUTH_PORT}/'
    print(f"Opening browser to: {auth_url}")
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually navigate to: {auth_url}")
    
    # Wait for authentication to complete
    print("Waiting for user authentication...")
    success = auth_completed.wait(timeout=300)  # 5 minute timeout
    
    if success:
        print("✅ Authentication successful!")
        # Give a moment for the shutdown response to be sent
        time.sleep(2)
        return True
    else:
        print("❌ Authentication timeout!")
        return False

def run_server():
    """Run Flask server."""
    global flask_server
    try:
        # Store server reference for shutdown
        flask_server = app
        app.run(host='127.0.0.1', port=AUTH_PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"Server error: {e}")

@app.route('/')
def index():
    return render_template('auth/index.html')

@app.route('/auth', methods=['POST'])
def authenticate():
    """Handle authentication request."""
    try:
        # Mock authentication - always accept
        print("User authentication received")
        
        # Set the authentication completed flag
        auth_completed.set()
        
        return jsonify({'status': 'success', 'message': 'Authentication successful'})
    except Exception as e:
        print(f"Authentication error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Handle shutdown request."""
    try:
        print("Shutting down auth server...")
        
        # Shutdown Flask server gracefully
        def shutdown_server():
            time.sleep(1)
            # Kill the process on this port to force shutdown
            kill_process_on_port(AUTH_PORT)
        
        threading.Thread(target=shutdown_server, daemon=True).start()
        return jsonify({'status': 'shutting_down'})
    except Exception as e:
        print(f"Shutdown error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
