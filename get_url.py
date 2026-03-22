import re
try:
    with open('tunnel_log.txt', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
        if match:
            print(match.group(0))
        else:
            print("URL NOT FOUND")
except Exception as e:
    print(f"ERROR: {str(e)}")
