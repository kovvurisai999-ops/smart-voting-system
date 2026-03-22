import socket
import logging
from zeroconf import IPVersion, ServiceInfo, Zeroconf
import time

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Use a dummy connect to find outgoing interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return socket.gethostbyname(socket.gethostname())

def start_broadcast():
    local_ip = get_local_ip()
    port = 5000
    hostname = "smart-voting"
    
    print(f"--- Broadcasting Local Service ---")
    print(f"Name: {hostname}.local")
    print(f"IP:   {local_ip}")
    print(f"Port: {port}")

    desc = {'path': '/'}
    info = ServiceInfo(
        "_http._tcp.local.",
        f"{hostname}._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties=desc,
        server=f"{hostname}.local.",
    )

    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    print(f"Registration of service {hostname}.local starting...")
    zeroconf.register_service(info)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        zeroconf.unregister_service(info)
        zeroconf.close()

if __name__ == '__main__':
    start_broadcast()
