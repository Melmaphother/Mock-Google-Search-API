# Mock-Google-Search-API 🕷️

本项目是一个基于 Python 的网络爬虫工具，用于模拟搜索引擎 API。它接收一个查询列表，为每个查询执行 Google 搜索，然后抓取顶部搜索结果的网页内容。该工具对于需要大量收集数据用于研究和实验，但又希望避免官方搜索 API 高昂费用的场景非常有用。

## 功能特性

-   **反机器人检测**: 使用 `undetected-chromedriver` 来模拟真实用户，以绕过许多常见的反机器人机制。
-   **会话持久化**: 将浏览器会话数据（如 Cookies）保存到本地配置文件中，有助于避免重复的人机验证（CAPTCHA）。
-   **多查询处理**: 可以批量处理一个查询列表。
-   **结构化输出**: 将每个查询的结果保存在输出目录中一个独立的、文件名经过处理的 `.jsonl` 文件里。
-   **代理支持**: 可以轻松配置以使用代理服务器发送请求。

## ⚙️ 环境要求

-   Python 3.10 或更高版本
-   系统中已安装 **Google Chrome** 浏览器。
-   使用 Conda 进行环境管理。

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
    -   **设置Chrome版本 (非常重要!)**: 打开 `google-web-crawler.py` 文件，找到这一行：
        ```python
        driver = uc.Chrome(options=options, version_main=138)
        ```
        你**必须**将 `138` 修改为你电脑上安装的 Google Chrome 浏览器的主版本号。例如，如果你的Chrome版本为 `139.0.7258.67`，那么主版本号就是 `139`。你可以在浏览器的 `chrome://settings/help` 页面找到你的版本号。

    -   **编辑查询列表**: 修改 `queries_to_process` 列表，填入你需要处理的搜索词。
        ```python
        queries_to_process = [
            "你的第一个查询",
            "你的第二个查询",
        ]
        ```
    -   **(可选) 配置代理**: 如果你需要使用代理，请设置 `proxy_server` 变量。
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

-   所有结果都保存在 `search_outputs/` 目录中。
-   每个查询都会生成一个 `.jsonl` 文件，文件中的每一行都是一个代表已抓取网页的 JSON 对象。
-   文件名是根据查询内容生成的安全版本（例如, `What_is_transformer.jsonl`）。

输出文件中的每个 JSON 对象都包含以下键值对：

-   `idx` (整数): 结果在 Google 搜索页上的从 0 开始的索引。
-   `title` (字符串): 搜索结果链接的标题。
-   `date` (字符串 | null): 从子页面提取的发布日期，如果可用。
-   `google_snippet` (字符串): Google 搜索结果页面上显示的简短摘要。
-   `subpage_snippet` (字符串 | null): 从子页面本身提取的 description 元标签内容，如果可用。
-   `source` (字符串): 结果的域名 (例如, `en.wikipedia.org`)。
-   `link` (字符串): 指向网页的直接 URL。
-   `content` (字符串): 从网页上抓取的主要文本内容。

