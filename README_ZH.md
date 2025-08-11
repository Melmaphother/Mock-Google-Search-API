# Mock-Google-Search-API 🕷️

本项目是一个基于 Python 的网络爬虫工具，用于模拟搜索引擎 API。它接收一个查询列表，为每个查询执行 Google 搜索，然后抓取顶部搜索结果的网页内容。该工具对于需要大量收集数据用于研究和实验，但又希望避免官方搜索 API 高昂费用的场景非常有用。

## 功能特性

- **反机器人检测**: 使用 `undetected-chromedriver` 来模拟真实用户，以绕过许多常见的反机器人机制。
- **会话持久化**: 将浏览器会话数据（如 Cookies）保存到本地配置文件中，有助于避免重复的人机验证（CAPTCHA）。
- **多查询处理**: 可以批量处理一个查询列表。
- **结构化输出**: 将每个查询的结果保存在输出目录中一个独立的、文件名经过处理的 `.jsonl` 文件里。
- **代理支持**: 可以轻松配置以使用代理服务器发送请求。

## ⚙️ 环境要求

- Python 3.10 或更高版本
- 系统中已安装 **Google Chrome** 浏览器。
- 使用 Conda 进行环境管理。

## 🚀 安装与配置

1.  **克隆代码库:**

    ```bash
    git clone https://github.com/Melmaphother/Mock-Google-Search-API.git
    cd Mock-Google-Search-API
    ```

2.  **创建并激活 Conda 环境:**

    ```bash
    conda create -n mock_api python=3.10
    conda activate mock_api
    ```

3.  **安装依赖:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **配置脚本 (`google-web-crawler.py`):**

    - **设置 Chrome 版本 (非常重要!)**: 打开 `google-web-crawler.py` 文件，找到这一行：

      ```python
      driver = uc.Chrome(options=options, version_main=139)
      ```

      你**必须**将 `138` 修改为你电脑上安装的 Google Chrome 浏览器的主版本号。例如，如果你的 Chrome 版本为 `139.0.7258.67`，那么主版本号就是 `139`。你可以在浏览器的 `chrome://settings/help` 页面找到你的版本号。

    - **编辑查询列表**: 修改 `queries_to_process` 列表，填入你需要处理的搜索词。
      ```python
      queries_to_process = [
          "你的第一个查询",
          "你的第二个查询",
      ]
      ```
    - **(可选) 配置代理**: 如果你需要使用代理，请设置 `proxy_server` 变量。
      ```python
      proxy_server = "http://user:password@host:port"
      ```

## 🔧 如何使用

1.  **运行脚本:**

    ```bash
    python google-web-crawler.py
    ```

2.  **首次运行**: 第一次运行脚本时，会弹出一个 Chrome 浏览器窗口。你可能会被要求进行人机验证或接受 Google 的服务条款。请遵循终端中打印的提示进行操作。当你在浏览器中看到正常的搜索结果后，回到终端并按 `Enter` 键继续。这个步骤是为了“预热”你的浏览器配置文件。

3.  **后续运行**: 在后续的运行中，脚本将重用已保存的配置文件，通常不再需要你进行手动操作。

## 📝 输出详情

- 所有结果都保存在 `search_outputs/` 目录中。
- 每个查询都会生成一个 `.jsonl` 文件，文件中的每一行都是一个代表已抓取网页的 JSON 对象。
- 文件名是根据查询内容生成的安全版本（例如, `What_is_transformer.jsonl`）。

输出文件中的每个 JSON 对象都包含以下键值对：

- `idx` (整数): 结果在 Google 搜索页上的从 0 开始的索引。
- `title` (字符串): 搜索结果链接的标题。
- `date` (字符串 | null): 从子页面提取的发布日期，如果可用。
- `google_snippet` (字符串): Google 搜索结果页面上显示的简短摘要。
- `subpage_snippet` (字符串 | null): 从子页面本身提取的 description 元标签内容，如果可用。
- `source` (字符串): 结果的域名 (例如, `en.wikipedia.org`)。
- `link` (字符串): 指向网页的直接 URL。
- `content` (字符串): 从网页上抓取的主要文本内容。

## 远程模式：服务器 + 本机 Chrome

本项目提供 `google-web-crawler-remote.py` 远程模式：在服务器（无 Chrome）上运行轻量 HTTP 队列服务，在你本机（有 Chrome）运行客户端领取任务、执行真实搜索并回传结果。

### 什么是 google-web-crawler-remote.py

- 服务器：内存任务队列与结果收集，支持 token 与结果落盘。
- 客户端：在本机运行，拉取任务，调用 `google-web-crawler.py`（需本机 Chrome），回传结果。
- 入队：通过 CLI（带 `--server`）或直接 HTTP 调用提交任务到服务端。
- API：
  - GET `/api/status`
  - GET `/api/next`（客户端使用）
  - POST `/api/enqueue` { query, top_k, proxy }
  - POST `/api/result` { task_id, results, error }

在服务器启动服务端（在 服务器 上执行）：

```bash
python google-web-crawler-remote.py server \
  --host 0.0.0.0 --port 8765 \
  --token YOUR_TOKEN \
  --output-dir ./remote_outputs
```

注意：客户端使用前，请将本机 `google-web-crawler.py` 中的 `version_main` 调成本机 Chrome 主版本号。

### 仅用 HTTP（不用 SSH）

直接使用服务器公网 IP 与端口访问。需确保服务器防火墙/安全组放通 8765/TCP。这是网络允许时最简单的拓扑。

客户端（在 本机 上执行，有 Chrome）：

```bash
python google-web-crawler-remote.py client \
  --server http://<SERVER_IP>:8765 \
  --token YOUR_TOKEN \
  --crawler-script /path/to/google-web-crawler.py \
  --no-proxy
```

向正在运行的服务端入队（在 本机 或任意可达主机上执行）：

```bash
python google-web-crawler-remote.py enqueue \
  --server http://<SERVER_IP>:8765 \
  --token YOUR_TOKEN \
  --query "Latest advancements in large language models" \
  --top-k 3
```

查看状态（在 任意可达主机 上执行）：

```bash
curl -H "X-Auth-Token: YOUR_TOKEN" http://<SERVER_IP>:8765/api/status
```

说明：

- `--no-proxy` 使客户端对服务端请求忽略系统代理（避免公司代理导致 502）。
- 不带 `--server` 的 `enqueue` 仅入队到当前进程（演示用途）；要入队到运行中的服务端，请加 `--server`。
- 若网络不允许自定义端口，可用 80/443 或通过 Nginx 反代到 `127.0.0.1:8765`。

### 用 SSH 建立信道 —— 建议

若外网无法直连 8765，可在本机建立 SSH 本地端口转发，将本地端口映射到服务器 8765。

在本机建立隧道（在 本机 上执行，保持该终端开启）：

```bash
ssh -N -L 18765:127.0.0.1:8765 <user>@<SERVER_IP> -p PORT
```

其中：

- `-N`：不在远端执行命令，仅做端口转发
- `-L 18765:127.0.0.1:8765`：将本地 18765 端口映射到 服务器 的 127.0.0.1:8765
- `<user>@<SERVER_IP>`：SSH 登录用户名与服务器地址

通过隧道运行客户端（在 本机 上执行，无代理）：

```bash
python google-web-crawler-remote.py client \
  --server http://127.0.0.1:18765 \
  --no-proxy \
  --token YOUR_TOKEN \
  --crawler-script /path/to/google-web-crawler.py
```

通过隧道入队（在 本机 上执行）：

```bash
python google-web-crawler-remote.py enqueue \
  --server http://127.0.0.1:18765 \
  --no-proxy \
  --token YOUR_TOKEN \
  --query "Latest advancements in large language models" \
  --top-k 3
```

通过隧道查看状态（在 本机 上执行）：


```bash
curl --noproxy '*' -H "X-Auth-Token: YOUR_TOKEN" http://127.0.0.1:18765/api/status
```
