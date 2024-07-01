import subprocess
import ipaddress
import socket
import re
import netifaces
import concurrent.futures
import time

def get_local_ip():
    try:
        # Get all network interfaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if not ip.startswith('127.'):
                        return ip
    except:
        # Fallback method if netifaces fails
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

def ping(ip):
    try:
        output = subprocess.check_output(["ping", "-n", "1", "-w", "500", ip], universal_newlines=True)
        if "TTL=" in output:
            return True
    except subprocess.CalledProcessError:
        pass
    return False

def get_mac(ip):
    try:
        output = subprocess.check_output(["arp", "-a", ip], universal_newlines=True)
        mac = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", output)
        if mac:
            return mac.group()
    except subprocess.CalledProcessError:
        pass
    return "Unknown"

def scan_ip(ip):
    if ping(str(ip)):
        mac = get_mac(str(ip))
        return {'ip': str(ip), 'mac': mac}
    return None

def main():
    local_ip = ipaddress.ip_address(get_local_ip())
    subnet = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    
    print(f"Local IP: {local_ip}")
    print(f"Scanning network: {subnet}")
    
    start_time = time.time()
    total_ips = subnet.num_addresses - 2  # Subtract network and broadcast addresses
    
    devices = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_ip = {executor.submit(scan_ip, ip): ip for ip in subnet.hosts()}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_ip), 1):
            result = future.result()
            if result:
                devices.append(result)
            
            # Update progress
            progress = (i / total_ips) * 100
            elapsed_time = time.time() - start_time
            est_total_time = elapsed_time / (i / total_ips)
            remaining_time = est_total_time - elapsed_time
            
            print(f"\rProgress: {progress:.1f}% | Elapsed: {elapsed_time:.1f}s | Remaining: {remaining_time:.1f}s", end="")
    
    print("\n\nDevices found on the network:")
    for device in devices:
        print(f"IP: {device['ip']:<15} MAC: {device['mac']}")
    
    total_time = time.time() - start_time
    print(f"\nTotal scan time: {total_time:.1f} seconds")

if __name__ == "__main__":
    main()