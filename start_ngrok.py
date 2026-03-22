import subprocess
import re
import time
import sys

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

# 2. Start Ngrok Tunnel
print("--- Starting Ngrok Tunnel ---")
# Use npx -y ngrok http 5000
ng_cmd = 'npx -y ngrok http 5000'
ng_proc = subprocess.Popen(ng_cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            text=True,
                            shell=True,
                            encoding='utf-8',
                            errors='replace')

live_url = None
start_time = time.time()

try:
    while True: # Keep alive indefinitely
        line = ng_proc.stdout.readline()
        if not line:
            break
        
        # Look for the ngrok URL
        if 'https://' in line:
            match = re.search(r'https://[a-z0-9.-]+\.ngrok-free\.app|https://[a-z0-9.-]+\.ngrok\.io', line)
            if match and not live_url:
                live_url = match.group(0)
                print(f"\n🚀 SUCCESS! YOUR NEW LIVE LINK IS: {live_url}")
                with open('LIVE_LINK.txt', 'w') as f:
                    f.write(f"PUBLIC_URL={live_url}\n")
            
except KeyboardInterrupt:
    print("Stopping...")
finally:
    print("Cleaning up...")
    flask_proc.terminate()
    ng_proc.terminate()
