# Start server (run on SERVER)
python google-web-crawler-remote.py server --host 0.0.0.0 --port 8765 --token YOUR_TOKEN --output-dir ./remote_outputs

# Client (HTTP mode, run on CLIENT/local machine)
python google-web-crawler-remote.py client --server http://<SERVER_IP>:8765 --token YOUR_TOKEN --crawler-script google-web-crawler.py --no-proxy

# Enqueue (HTTP mode, run on CLIENT or any host that can reach SERVER)
python google-web-crawler-remote.py enqueue --server http://<SERVER_IP>:8765 --token YOUR_TOKEN --query "Latest advancements in large language models" --top-k 3

# Create SSH tunnel (run on CLIENT; keep this session open)
ssh -N -L 18765:127.0.0.1:8765 <user>@<SERVER_IP> -p PORT

# Client over SSH tunnel (run on CLIENT)
python google-web-crawler-remote.py client --server http://127.0.0.1:18765 --no-proxy --token YOUR_TOKEN --crawler-script google-web-crawler.py

# Enqueue over SSH tunnel (run on CLIENT)
python google-web-crawler-remote.py enqueue --server http://127.0.0.1:18765 --no-proxy --token YOUR_TOKEN --query "Latest advancements in large language models" --top-k 3

# Check status over SSH tunnel (run on CLIENT)
curl --noproxy '*' http://127.0.0.1:18765/api/status -H "X-Auth-Token: YOUR_TOKEN"