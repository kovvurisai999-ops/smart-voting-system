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

# 2. Start mDNS Broadcast (Local Hostname)
print("--- Starting mDNS Broadcast (smart-voting.local) ---")
mdns_proc = subprocess.Popen(['venv\\Scripts\\python.exe', 'broadcast_service.py'],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

time.sleep(5) 

# 3. Start Pinggy Tunnel
print("--- Starting Pinggy Tunnel ---")
png_cmd = 'npx -y pinggy -p 5000'
png_proc = subprocess.Popen(png_cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            text=True,
                            shell=True,
                            encoding='utf-8',
                            errors='replace')

live_url = None

try:
    while True:
        line = png_proc.stdout.readline()
        if not line:
            break
        # Print quietly, but look for URL
        if 'https://' in line:
            match = re.search(r'https://[a-z0-9.-]+\.pinggy\.[a-z]+', line)
            if match and not live_url:
                live_url = match.group(0)
                print(f"\n🚀 SUCCESS! YOUR NEW LIVE LINK IS: {live_url}")
                with open('LIVE_LINK.txt', 'w') as f:
                    f.write(f"PUBLIC_URL={live_url}\n")
            
except KeyboardInterrupt:
    print("Stopping...")
finally:
    flask_proc.terminate()
    png_proc.terminate()
