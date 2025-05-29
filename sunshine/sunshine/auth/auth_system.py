#!/usr/bin/env python3
import sys
import time
import os
from flask import Flask, render_template_string, request, jsonify
import threading
import webbrowser

app = Flask(__name__)
auth_completed = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sunshine Authentication</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .auth-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .version {
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .auth-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .auth-button:hover {
            background: #5a5fdb;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }
        .auth-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .status {
            margin-top: 20px;
            font-size: 16px;
            color: #666;
        }
        .success { color: #4caf50; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>🌞 Sunshine System</h1>
        <div class="version">Minimal Test Version</div>
        <p>Click to authenticate and start the system</p>
        <button id="authBtn" class="auth-button" onclick="authenticate()">Authenticate</button>
        <div id="status" class="status"></div>
    </div>
    
    <script>
        function authenticate() {
            const btn = document.getElementById('authBtn');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            status.textContent = 'Authenticating...';
            status.className = 'status';
            
            fetch('/auth', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        status.textContent = '✅ Authentication successful! Starting system...';
                        status.className = 'status success';
                        setTimeout(() => {
                            window.close();
                        }, 1500);
                    } else {
                        status.textContent = '❌ Authentication failed!';
                        status.className = 'status error';
                        btn.disabled = false;
                    }
                })
                .catch(error => {
                    status.textContent = '❌ Error: ' + error;
                    status.className = 'status error';
                    btn.disabled = false;
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/auth', methods=['POST'])
def auth():
    global auth_completed
    auth_completed = True
    return jsonify({"success": True})

def run_server():
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("Authentication server started at http://127.0.0.1:5000")
    time.sleep(0.5)
    webbrowser.open('http://127.0.0.1:5000')
    
    while not auth_completed:
        time.sleep(0.1)
    
    print("Authentication completed successfully")
    time.sleep(0.5)
    os._exit(0)
