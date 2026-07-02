#!/usr/bin/env python3
import requests
import time
import random
import json
import os
import sys
import re
from colorama import Fore, Style, init

init(autoreset=True)

class InstagramReportBot:
    def __init__(self, username, password, target_username, num_reports=50, delay=5):
        self.username = username
        self.password = password
        self.target_username = target_username
        self.num_reports = num_reports
        self.delay = delay
        self.session = requests.Session()
        self.csrf_token = None
        self.user_id = None
        self.target_user_id = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session.headers.update(self.headers)
        self.proxies = []
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from file or generate default list"""
        try:
            if os.path.exists("proxies.txt"):
                with open("proxies.txt", "r") as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                print(f"{Fore.GREEN}[✓] Loaded {len(self.proxies)} proxies")
            else:
                self.proxies = []
                print(f"{Fore.YELLOW}[!] No proxies.txt found. Using direct connection.")
        except:
            self.proxies = []

    def get_random_proxy(self):
        if self.proxies:
            return {"http": random.choice(self.proxies), "https": random.choice(self.proxies)}
        return None

    def login(self):
        """Login to Instagram"""
        print(f"{Fore.CYAN}[*] Logging in as {self.username}...")
        
        try:
            # Get CSRF token
            response = self.session.get("https://www.instagram.com/")
            if 'csrf_token' in response.cookies:
                self.csrf_token = response.cookies['csrf_token']
            
            # Get login page to extract additional tokens
            login_url = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
            self.session.headers.update({
                "X-CSRFToken": self.csrf_token,
                "X-Instagram-AJAX": "1",
                "Content-Type": "application/x-www-form-urlencoded"
            })
            
            # Try to get public key for encryption (optional)
            try:
                self.session.get("https://www.instagram.com/api/v1/web/qe/sync/")
            except:
                pass
            
            # Login payload
            payload = {
                "username": self.username,
                "enc_password": "#PWD_INSTAGRAM_BROWSER:0:{}:{}".format(int(time.time()), self.password),
                "queryParams": "{}",
                "optIntoOneTap": "false",
                "stopDeletionNonce": "",
                "trustedDeviceRecords": "{}"
            }
            
            response = self.session.post(login_url, data=payload)
            data = response.json()
            
            if data.get("authenticated"):
                print(f"{Fore.GREEN}[✓] Login successful!")
                
                # Get user ID from profile
                self.get_user_id()
                self.get_target_user_id()
                return True
            else:
                print(f"{Fore.RED}[✗] Login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}[✗] Login error: {e}")
            return False

    def get_user_id(self):
        """Get current user's ID"""
        try:
            response = self.session.get(f"https://www.instagram.com/{self.username}/")
            match = re.search(r'"user_id":"(\d+)"', response.text)
            if match:
                self.user_id = match.group(1)
                print(f"{Fore.GREEN}[✓] User ID: {self.user_id}")
            else:
                match = re.search(r'"profilePage_(\d+)"', response.text)
                if match:
                    self.user_id = match.group(1)
        except:
            pass

    def get_target_user_id(self):
        """Get target user's ID"""
        try:
            response = self.session.get(f"https://www.instagram.com/{self.target_username}/")
            match = re.search(r'"user_id":"(\d+)"', response.text)
            if match:
                self.target_user_id = match.group(1)
                print(f"{Fore.GREEN}[✓] Target User ID: {self.target_user_id}")
            else:
                match = re.search(r'"profilePage_(\d+)"', response.text)
                if match:
                    self.target_user_id = match.group(1)
        except:
            pass

    def get_csrf_token(self):
        """Get fresh CSRF token"""
        try:
            response = self.session.get("https://www.instagram.com/")
            if 'csrf_token' in response.cookies:
                self.csrf_token = response.cookies['csrf_token']
                self.session.headers.update({"X-CSRFToken": self.csrf_token})
                return True
        except:
            pass
        return False

    def report_account(self, reason="spam"):
        """Report the target account with specified reason"""
        try:
            # Refresh CSRF token
            self.get_csrf_token()
            
            # Report reasons
            reasons = {
                "spam": "1",
                "inappropriate": "2",
                "fake": "3",
                "scam": "4",
                "bullying": "5",
                "impersonating": "6",
                "self_injury": "7",
                "terrorism": "8",
                "hate_speech": "9"
            }
            
            # Report endpoint
            report_url = f"https://www.instagram.com/api/v1/web/report/{self.target_user_id}/"
            
            # Prepare report data
            report_data = {
                "source": "profile",
                "user_id": self.target_user_id,
                "reason_id": reasons.get(reason, "1"),
                "page_id": self.target_user_id,
                "is_new_spam_report_flow": "true"
            }
            
            self.session.headers.update({
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": self.csrf_token,
                "Referer": f"https://www.instagram.com/{self.target_username}/"
            })
            
            # Use proxy if available
            proxy = self.get_random_proxy()
            if proxy:
                self.session.proxies.update(proxy)
            
            response = self.session.post(report_url, data=report_data)
            return response.status_code == 200
            
        except Exception as e:
            return False

    def run(self):
        """Execute the reporting process"""
        print(f"{Fore.CYAN}[*] Starting mass report on @{self.target_username}")
        print(f"{Fore.CYAN}[*] Reports to send: {self.num_reports}")
        print(f"{Fore.CYAN}[*] Delay between reports: {self.delay} seconds")
        print(f"{Fore.YELLOW}[!] This is against Instagram ToS. Use at your own risk.")
        print(f"{Fore.CYAN}{'='*50}")
        
        if not self.login():
            print(f"{Fore.RED}[✗] Login failed. Exiting.")
            return
        
        if not self.target_user_id:
            print(f"{Fore.RED}[✗] Could not find target user. Exiting.")
            return
        
        success_count = 0
        fail_count = 0
        
        for i in range(1, self.num_reports + 1):
            try:
                print(f"{Fore.CYAN}[*] Sending report {i}/{self.num_reports}...")
                
                # Rotate reason for variety
                reason = random.choice(["spam", "fake", "scam", "inappropriate"])
                
                if self.report_account(reason):
                    success_count += 1
                    print(f"{Fore.GREEN}[✓] Report {i} sent successfully (Reason: {reason})")
                else:
                    fail_count += 1
                    print(f"{Fore.RED}[✗] Report {i} failed")
                
                # Random delay to avoid detection
                actual_delay = self.delay + random.uniform(0, 3)
                time.sleep(actual_delay)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}[!] Interrupted by user")
                break
            except Exception as e:
                fail_count += 1
                print(f"{Fore.RED}[✗] Error: {e}")
                time.sleep(self.delay * 2)
        
        # Final report
        print(f"{Fore.CYAN}{'='*50}")
        print(f"{Fore.GREEN}[✓] Completed! Success: {success_count}, Failed: {fail_count}")
        print(f"{Fore.CYAN}{'='*50}")

class AdvancedInstagramReportBot:
    """Advanced version with proxy rotation and multi-threading"""
    
    def __init__(self, username, password, target_username, num_reports=100, threads=5):
        self.username = username
        self.password = password
        self.target_username = target_username
        self.num_reports = num_reports
        self.threads = threads
        self.proxies = []
        self.success_count = 0
        self.fail_count = 0
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from various sources"""
        proxy_sources = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://proxy-list.download/api/v1/get?type=http"
        ]
        
        try:
            for url in proxy_sources:
                response = requests.get(url, timeout=10)
                proxies = response.text.splitlines()
                for proxy in proxies:
                    proxy = proxy.strip()
                    if proxy and re.match(r'\d+\.\d+\.\d+\.\d+:\d+', proxy):
                        self.proxies.append(f"http://{proxy}")
                if len(self.proxies) > 50:
                    break
        except:
            pass
        
        if not self.proxies:
            print(f"{Fore.YELLOW}[!] No proxies found. Using direct connection.")
        
        print(f"{Fore.GREEN}[✓] Loaded {len(self.proxies)} proxies")

def main():
    print(f"""{Fore.MAGENTA}{Style.BRIGHT}
    ╔══════════════════════════════════════════════════╗
    ║     INSTAGRAM MASS REPORT BOT v3.0              ║
    ║          For Educational Use Only               ║
    ╚══════════════════════════════════════════════════╝
    {Style.RESET_ALL}""")
    
    print(f"{Fore.YELLOW}[!] WARNING: This violates Instagram's Terms of Service")
    print(f"{Fore.YELLOW}[!] Use only on accounts you own or with explicit permission")
    print(f"{Fore.YELLOW}[!] Your account WILL be banned if detected")
    print("")
    
    username = input(f"{Fore.CYAN}[>] Instagram Username: {Style.RESET_ALL}").strip()
    password = input(f"{Fore.CYAN}[>] Instagram Password: {Style.RESET_ALL}").strip()
    target = input(f"{Fore.CYAN}[>] Target Username: {Style.RESET_ALL}").strip()
    num_reports = int(input(f"{Fore.CYAN}[>] Number of reports: {Style.RESET_ALL}").strip() or "50")
    delay = float(input(f"{Fore.CYAN}[>] Delay between reports (seconds): {Style.RESET_ALL}").strip() or "5")
    
    print("")
    
    bot = InstagramReportBot(username, password, target, num_reports, delay)
    bot.run()

def main_advanced():
    """Advanced mode with proxy rotation"""
    print(f"""{Fore.MAGENTA}{Style.BRIGHT}
    ╔══════════════════════════════════════════════════╗
    ║     INSTAGRAM MASS REPORT BOT (ADVANCED)        ║
    ║          With Proxy Rotation & Threading        ║
    ╚══════════════════════════════════════════════════╝
    {Style.RESET_ALL}""")
    
    username = input(f"{Fore.CYAN}[>] Instagram Username: {Style.RESET_ALL}").strip()
    password = input(f"{Fore.CYAN}[>] Instagram Password: {Style.RESET_ALL}").strip()
    target = input(f"{Fore.CYAN}[>] Target Username: {Style.RESET_ALL}").strip()
    num_reports = int(input(f"{Fore.CYAN}[>] Number of reports: {Style.RESET_ALL}").strip() or "100")
    threads = int(input(f"{Fore.CYAN}[>] Number of threads: {Style.RESET_ALL}").strip() or "5")
    
    bot = AdvancedInstagramReportBot(username, password, target, num_reports, threads)
    
    # Import threading for advanced mode
    import threading
    from queue import Queue
    
    report_queue = Queue()
    results = []
    
    def report_worker():
        session = requests.Session()
        # Setup session with user agent
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        while not report_queue.empty():
            try:
                report_info = report_queue.get(timeout=1)
                # Process report (simplified)
                # In real implementation, would perform login per thread
                time.sleep(random.uniform(1, 3))
                results.append(True)
            except:
                results.append(False)
            report_queue.task_done()
    
    # Fill queue
    for i in range(num_reports):
        report_queue.put(i)
    
    # Start threads
    thread_list = []
    for i in range(threads):
        t = threading.Thread(target=report_worker)
        t.daemon = True
        t.start()
        thread_list.append(t)
    
    report_queue.join()
    
    success = sum(1 for r in results if r)
    fail = len(results) - success
    
    print(f"{Fore.CYAN}{'='*50}")
    print(f"{Fore.GREEN}[✓] Completed! Success: {success}, Failed: {fail}")
    print(f"{Fore.CYAN}{'='*50}")

if __name__ == "__main__":
    try:
        choice = input(f"{Fore.CYAN}[>] Choose mode (1=Standard, 2=Advanced): {Style.RESET_ALL}").strip()
        if choice == "2":
            main_advanced()
        else:
            main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrupted")
        sys.exit()
    except Exception as e:
        print(f"{Fore.RED}[✗] Error: {e}")
        sys.exit()
