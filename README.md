# Mock-Google-Search-API 🕷️

This project is a Python-based web scraping tool that simulates a search engine API. It takes a list of queries, performs a Google search for each, and then scrapes the content from the top search results. This is useful for gathering data for research and experiments without incurring the high costs of official search APIs.

## Features

-   **Anti-Bot Detection**: Uses `undetected-chromedriver` to appear more like a real user, bypassing many common anti-bot mechanisms.
-   **Persistent Session**: Saves browser session data (cookies, etc.) to a local profile, which helps in avoiding repeated CAPTCHA challenges.
-   **Multi-Query Processing**: Processes a list of search queries in a batch.
-   **Organized Output**: Saves the results for each query in a separate, sanitized `.jsonl` file inside an output directory.
-   **Proxy Support**: Easily configurable to use a proxy server for requests.

## ⚙️ Prerequisites

-   Python 3.10+
-   **Google Chrome** browser installed on your system.
-   Conda for environment management.

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
    -   **Set Chrome Version (Crucial!)**: Open `google-web-crawler.py` and find this line:
        ```python
        driver = uc.Chrome(options=options, version_main=139)
        ```
        You **must** change `138` to the major version of your installed Google Chrome browser. For example, if your Chrome version is `139.0.7258.67`, the major version is `139`. You can find your version at `chrome://settings/help`.

    -   **Edit Query List**: Modify the `queries_to_process` list to include the search terms you want to process.
        ```python
        queries_to_process = [
            "Your first query",
            "Your second query",
        ]
        ```
    -   **(Optional) Configure Proxy**: If you need to use a proxy, set the `proxy_server` variable.
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

-   The results are saved in the `search_outputs/` directory.
-   Each query generates a `.jsonl` file, where each line is a JSON object representing a single scraped web page.
-   The filename is a sanitized version of the query (e.g., `What_is_transformer.jsonl`).

Each JSON object in the output file has the following key-value structure:

-   `idx` (integer): The 0-based index of the result from the Google search page.
-   `title` (string): The title of the search result link.
-   `date` (string | null): The publication date extracted from the sub-page, if available.
-   `google_snippet` (string): The short summary shown on the Google search results page.
-   `subpage_snippet` (string | null): The description meta tag content from the sub-page itself, if available.
-   `source` (string): The domain name of the result (e.g., `en.wikipedia.org`).
-   `link` (string): The direct URL to the web page.
-   `content` (string): The main text content scraped from the web page.

