# Mock-Google-Search-API 🕷️

This project is a Python-based web scraping tool that simulates a search engine API. It takes a list of queries, performs a Google search for each, and then scrapes the content from the top search results. This is useful for gathering data for research and experiments without incurring the high costs of official search APIs.

## Features

- **Anti-Bot Detection**: Uses `undetected-chromedriver` to appear more like a real user, bypassing many common anti-bot mechanisms.
- **Persistent Session**: Saves browser session data (cookies, etc.) to a local profile, which helps in avoiding repeated CAPTCHA challenges.
- **Multi-Query Processing**: Processes a list of search queries in a batch.
- **Organized Output**: Saves the results for each query in a separate, sanitized `.jsonl` file inside an output directory.
- **Proxy Support**: Easily configurable to use a proxy server for requests.

## ⚙️ Prerequisites

- Python 3.10+
- **Google Chrome** browser installed on your system.
- Conda for environment management.

## 🚀 Setup & Configuration

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Melmaphother/Mock-Google-Search-API.git
    cd Mock-Google-Search-API
    ```

2.  **Create and activate a Conda environment:**

    ```bash
    conda create -n mock_api python=3.10
    conda activate mock_api
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the script (`google-web-crawler.py`):**

    - **Set Chrome Version (Crucial!)**: Open `google-web-crawler.py` and find this line:

      ```python
      driver = uc.Chrome(options=options, version_main=139)
      ```

      You **must** change `138` to the major version of your installed Google Chrome browser. For example, if your Chrome version is `139.0.7258.67`, the major version is `139`. You can find your version at `chrome://settings/help`.

    - **Edit Query List**: Modify the `queries_to_process` list to include the search terms you want to process.
      ```python
      queries_to_process = [
          "Your first query",
          "Your second query",
      ]
      ```
    - **(Optional) Configure Proxy**: If you need to use a proxy, set the `proxy_server` variable.
      ```python
      proxy_server = "http://user:password@host:port"
      ```

## 🔧 Usage

1.  **Run the script:**

    ```bash
    python google-web-crawler.py
    ```

2.  **First-Time Run**: The first time you run the script, a Chrome window will open. You may be required to solve a CAPTCHA or accept Google's terms. Follow the instructions printed in your terminal. Once you see the search results in the browser, press `Enter` in the terminal to continue. This step "warms up" your browser profile.

3.  **Subsequent Runs**: On subsequent runs, the script will reuse the saved profile, and you should not be required to perform manual steps.

## 📝 Output Details

- The results are saved in the `search_outputs/` directory.
- Each query generates a `.jsonl` file, where each line is a JSON object representing a single scraped web page.
- The filename is a sanitized version of the query (e.g., `What_is_transformer.jsonl`).

Each JSON object in the output file has the following key-value structure:

- `idx` (integer): The 0-based index of the result from the Google search page.
- `title` (string): The title of the search result link.
- `date` (string | null): The publication date extracted from the sub-page, if available.
- `google_snippet` (string): The short summary shown on the Google search results page.
- `subpage_snippet` (string | null): The description meta tag content from the sub-page itself, if available.
- `source` (string): The domain name of the result (e.g., `en.wikipedia.org`).
- `link` (string): The direct URL to the web page.
- `content` (string): The main text content scraped from the web page.

## Remote Mode: Server + Local Chrome

This project also supports a remote mode via `google-web-crawler-remote.py`. Run a lightweight HTTP queue on a server (without Chrome), and run the client on your local machine (with Chrome) to perform real searches and upload results back.

### What is google-web-crawler-remote.py

- Server: in-memory task queue and result collection, with optional token and result file output.
- Client: runs locally, pulls tasks from the server, executes `google-web-crawler.py` (Chrome required), and posts results to the server.
- Enqueue: submit tasks to the running server via CLI (`--server`) or raw HTTP.
- APIs:
  - GET `/api/status`
  - GET `/api/next` (client use)
  - POST `/api/enqueue` { query, top_k, proxy }
  - POST `/api/result` { task_id, results, error }

Start the server (run on SERVER):

```bash
python google-web-crawler-remote.py server \
  --host 0.0.0.0 --port 8765 \
  --token YOUR_TOKEN \
  --output-dir ./remote_outputs
```

Note: On the client, you must set the correct `version_main` in `google-web-crawler.py` to match your local Chrome major version.

### HTTP only (no SSH)

Use the server's public IP and port directly. Ensure inbound 8765/TCP is allowed by firewall/security groups. This is the simplest topology if your network permits it.

Client (run on CLIENT/local machine with Chrome):

```bash
python google-web-crawler-remote.py client \
  --server http://<SERVER_IP>:8765 \
  --token YOUR_TOKEN \
  --crawler-script /path/to/google-web-crawler.py \
  --no-proxy
```

Enqueue a task to the running server (run on CLIENT or any host that can reach SERVER):

```bash
python google-web-crawler-remote.py enqueue \
  --server http://<SERVER_IP>:8765 \
  --token YOUR_TOKEN \
  --query "Latest advancements in large language models" \
  --top-k 3
```

Check status (from any host that can reach SERVER):

```bash
curl -H "X-Auth-Token: YOUR_TOKEN" http://<SERVER_IP>:8765/api/status
```

Notes:

- `--no-proxy` tells the client to ignore system proxies for server requests (helps avoid 502 via corporate proxies).
- The CLI `enqueue` without `--server` enqueues into the current process only (for demo). Use `--server` to send tasks to the running server.
- Some networks block custom ports; consider running on 80/443 or placing Nginx in front to reverse-proxy to `127.0.0.1:8765`.

### With SSH tunnel – recommend

If direct inbound to 8765 is blocked, create a local SSH tunnel that forwards a local port to the server's 8765.

Create tunnel (run on CLIENT/local machine; keep this session open):

```bash
ssh -N -L 18765:127.0.0.1:8765 <user>@<SERVER_IP> -p PORT
```

Where:

- `-N`: do not execute remote commands (just port forwarding)
- `-L 18765:127.0.0.1:8765`: bind local port 18765 and forward to SERVER's 127.0.0.1:8765
- `<user>@<SERVER_IP>`: your SSH username and server IP/host

Client over the tunnel (run on CLIENT/local machine, no proxy):

```bash
python google-web-crawler-remote.py client \
  --server http://127.0.0.1:18765 \
  --no-proxy \
  --token YOUR_TOKEN \
  --crawler-script /path/to/google-web-crawler.py
```

Enqueue via the tunnel (run on CLIENT/local machine):

```bash
python google-web-crawler-remote.py enqueue \
  --server http://127.0.0.1:18765 \
  --no-proxy \
  --token YOUR_TOKEN \
  --query "Latest advancements in large language models" \
  --top-k 3
```

Check status via the tunnel (run on CLIENT/local machine):

```bash
curl --noproxy '*' -H "X-Auth-Token: YOUR_TOKEN" http://127.0.0.1:18765/api/status
```
