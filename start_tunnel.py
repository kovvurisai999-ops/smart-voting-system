import subprocess
import re
import time
import os
import signal

# 1. Start Flask App
print("--- Starting Flask App ---")
flask_proc = subprocess.Popen(['venv\\Scripts\\python.exe', 'app.py'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)

time.sleep(5) # Give Flask time to bind port 5000

# 2. Start Cloudflare Tunnel
print("--- Starting Cloudflare Tunnel ---")
cf_cmd = 'npx -y cloudflared tunnel --url http://127.0.0.1:5000'
cf_proc = subprocess.Popen(cf_cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            text=True,
                            shell=True)

live_url = None
start_time = time.time()

try:
    while True: # Keep alive indefinitely
        line = cf_proc.stdout.readline()
        if not line:
            break
        print(f"[TUNNEL LOG]: {line.strip()}")
        
        # Look for the trycloudflare URL
        match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
        if match and not live_url:
            live_url = match.group(0)
            print(f"\n🚀 SUCCESS! YOUR LIVE LINK IS: {live_url}")
            with open('LIVE_LINK.txt', 'w') as f:
                f.write(f"PUBLIC_URL={live_url}\n")
            # Don't break! Stay alive to keep processes running.
            
except KeyboardInterrupt:
    print("Stopping...")
finally:
    print("Cleaning up...")
    flask_proc.terminate()
    cf_proc.terminate()
