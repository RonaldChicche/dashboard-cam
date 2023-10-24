import nmap
import socket

def get_ip_address():
    # Get IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address

# Set up nmap scanner
scanner = nmap.PortScanner()

# Get IP address and keyword from user input
ip_address = get_ip_address()
print(f"IP address: {ip_address}")
keyword = input("Enter keyword: ")

# Scan network for devices
scanner.scan(hosts=f"{ip_address}/24", arguments="-sP")

# Print list of devices that match keyword
for host in scanner.all_hosts():
    # print hostnames
    if 'mac' in scanner[host]['addresses']:
        mac_address = scanner[host]['addresses']['mac']
        manufacturer = scanner[host]['vendor'][mac_address]
        if keyword in manufacturer.lower():
            mac_address = scanner[host]['addresses']['mac']
            print(f"Device: {host} ({mac_address}) - Manufacturer: {manufacturer}")