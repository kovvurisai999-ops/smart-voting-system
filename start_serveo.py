import subprocess
import re
import time
import sys
import socket

# Helper to get local IP
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

local_ip = get_local_ip()
print(f"--- Local IP: {local_ip} ---")

# Set encoding for Windows CLI
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 1. Start Flask App
print("--- Starting Flask App ---")
flask_proc = subprocess.Popen(['venv\\Scripts\\python.exe', 'app.py'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)

time.sleep(5) 

# 2. Start Serveo Tunnel
print("--- Starting Serveo Tunnel ---")
# Use ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 serveo.net
srv_cmd = 'ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 serveo.net'
srv_proc = subprocess.Popen(srv_cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            text=True,
                            shell=True,
                            encoding='utf-8',
                            errors='replace')

live_url = None

try:
    while True: # Keep alive indefinitely
        line = srv_proc.stdout.readline()
        if not line:
            break
        print(f"[SERVEO LOG]: {line.strip()}")
        
        # Look for the serveo.net URL
        match = re.search(r'https://[a-z0-9.-]+\.serveo\.net', line)
        if match and not live_url:
            live_url = match.group(0)
            print(f"\n🚀 SUCCESS! YOUR NEW LIVE LINK IS: {live_url}")
            with open('LIVE_LINK.txt', 'w') as f:
                f.write(f"PUBLIC_URL={live_url}\n")
                f.write(f"LOCAL_IP_URL=http://{local_ip}:5000\n")
            
except KeyboardInterrupt:
    print("Stopping...")
finally:
    flask_proc.terminate()
    srv_proc.terminate()
