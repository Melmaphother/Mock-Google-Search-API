#!/usr/bin/env python3
import argparse
import json
import os
import queue
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


# ------------------------------
# Simple in-memory task queue and result storage
# ------------------------------


class Task:
    def __init__(self, query: str, top_k: int = 3, proxy: str | None = None, filter_year: int | None = None):
        self.id = str(uuid.uuid4())
        self.query = query
        self.top_k = int(top_k)
        self.proxy = proxy
        self.filter_year = filter_year
        self.status = "queued"  # queued -> running -> done/failed
        self.created_at = time.time()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.error: str | None = None


class TaskStore:
    def __init__(self):
        self._pending_q: queue.Queue[str] = queue.Queue()
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, list] = {}
        self._lock = threading.Lock()

    def enqueue(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task
            self._pending_q.put(task.id)
            return task.id

    def dequeue(self) -> Task | None:
        try:
            task_id = self._pending_q.get_nowait()
        except queue.Empty:
            return None
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.status = "running"
            task.started_at = time.time()
            return task

    def set_result(self, task_id: str, results: list | None, error: str | None = None):
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if error:
                task.status = "failed"
                task.error = str(error)
            else:
                task.status = "done"
                self._results[task_id] = results or []
            task.finished_at = time.time()
            return True

    def get_task(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> list | None:
        with self._lock:
            return self._results.get(task_id)

    def get_status(self) -> dict:
        with self._lock:
            summary = {
                "total": len(self._tasks),
                "queued": sum(1 for t in self._tasks.values() if t.status == "queued"),
                "running": sum(
                    1 for t in self._tasks.values() if t.status == "running"
                ),
                "done": sum(1 for t in self._tasks.values() if t.status == "done"),
                "failed": sum(1 for t in self._tasks.values() if t.status == "failed"),
            }
            tasks = [
                {
                    "id": t.id,
                    "query": t.query,
                    "top_k": t.top_k,
                    "proxy": t.proxy,
                    "filter_year": t.filter_year,
                    "status": t.status,
                    "error": t.error,
                    "created_at": t.created_at,
                    "started_at": t.started_at,
                    "finished_at": t.finished_at,
                }
                for t in self._tasks.values()
            ]
            return {"summary": summary, "tasks": tasks}


GLOBAL_STORE = TaskStore()


# ------------------------------
# HTTP server implementation (using standard library only)
# ------------------------------


class APIServerHandler(BaseHTTPRequestHandler):
    server_version = "CrawlerRemoteHTTP/1.0"

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            return json.loads(body.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _write_json(self, obj: dict | list, status: int = 200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _check_token(self) -> bool:
        # 允许 query 参数或 Header
        token_conf = getattr(self.server, "auth_token", None)
        if not token_conf:
            return True
        header_token = self.headers.get("X-Auth-Token")
        if header_token and header_token == token_conf:
            return True
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        query_token = qs.get("token", [None])[0]
        return query_token == token_conf

    def do_GET(self):
        if not self._check_token():
            self._write_json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/next":
            task = GLOBAL_STORE.dequeue()
            if not task:
                self._write_json({"message": "no_task"}, status=HTTPStatus.NO_CONTENT)
                return
            self._write_json(
                {
                    "task_id": task.id,
                    "query": task.query,
                    "top_k": task.top_k,
                    "proxy": task.proxy,
                    "filter_year": task.filter_year,
                }
            )
            return

        if path == "/api/status":
            self._write_json(GLOBAL_STORE.get_status())
            return

        if path.startswith("/api/result/"):
            task_id = path.split("/", 3)[-1]
            result = GLOBAL_STORE.get_result(task_id)
            task = GLOBAL_STORE.get_task(task_id)
            if task is None:
                self._write_json(
                    {"error": "task_not_found"}, status=HTTPStatus.NOT_FOUND
                )
                return
            self._write_json(
                {
                    "task": {
                        "id": task.id,
                        "status": task.status,
                        "error": task.error,
                    },
                    "results": result,
                }
            )
            return

        self._write_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if not self._check_token():
            self._write_json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/enqueue":
            data = self._read_json()
            query = (data.get("query") or "").strip()
            top_k = int(data.get("top_k") or 3)
            proxy = data.get("proxy")
            filter_year = data.get("filter_year")
            if filter_year is not None:
                filter_year = int(filter_year)
            
            if not query:
                self._write_json(
                    {"error": "query_required"}, status=HTTPStatus.BAD_REQUEST
                )
                return
            task = Task(query=query, top_k=top_k, proxy=proxy, filter_year=filter_year)
            task_id = GLOBAL_STORE.enqueue(task)
            self._write_json({"task_id": task_id})
            return

        if path == "/api/result":
            data = self._read_json()
            task_id = data.get("task_id")
            results = data.get("results")
            error = data.get("error")
            if not task_id:
                self._write_json(
                    {"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST
                )
                return
            ok = GLOBAL_STORE.set_result(task_id, results=results, error=error)
            if not ok:
                self._write_json(
                    {"error": "task_not_found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            # 如果配置了输出目录，落盘保存一份
            out_dir = getattr(self.server, "output_dir", None)
            if out_dir and not error and isinstance(results, list):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                    outfile = os.path.join(out_dir, f"{task_id}.jsonl")
                    with open(outfile, "w", encoding="utf-8") as f:
                        for item in results:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")
                except Exception as e:
                    # 不阻断主流程，写入失败只记录
                    sys.stderr.write(
                        f"[WARN] write results failed for {task_id}: {e}\n"
                    )

            self._write_json({"ok": True})
            return

        self._write_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)


def run_server(host: str, port: int, token: str | None, output_dir: str | None):
    httpd = HTTPServer((host, port), APIServerHandler)
    # 挂载配置到server对象上供Handler读取
    httpd.auth_token = token
    httpd.output_dir = output_dir
    print(
        f"[SERVER] listening on http://{host}:{port}  (token={'<none>' if not token else '***'})"
    )
    if output_dir:
        print(f"[SERVER] results will be saved to '{output_dir}'")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] shutting down...")
    finally:
        httpd.server_close()


# ------------------------------
# 客户端：在本机执行真实Chrome搜索并回传
# ------------------------------


def _load_crawler_module(crawler_script_path: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "crawler_local_module", crawler_script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load crawler script: {crawler_script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    required = [
        "search_google",
        "scrape_page_content",
        "simulate_search_api",
    ]
    for name in required:
        if not hasattr(module, name):
            raise RuntimeError(f"Crawler script missing required function: {name}")
    
    # Check if clean_chrome_profile function exists
    if hasattr(module, "clean_chrome_profile"):
        print("[CLIENT] Chrome profile cleanup function available")
    
    return module


def client_loop(
    server_base_url: str,
    token: str | None,
    crawler_script_path: str,
    poll_interval: float = 3.0,
    disable_http_proxy: bool = False,
):
    # 动态加载现有的 google-web-crawler.py
    module = _load_crawler_module(crawler_script_path)

    import urllib.request
    import urllib.error

    # 构建opener：当禁用代理时，忽略系统环境中的 http_proxy/https_proxy
    if disable_http_proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        print("[CLIENT] HTTP proxy disabled for server requests")
    else:
        opener = urllib.request.build_opener()

    def _headers():
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Auth-Token"] = token
        return headers

    def _url(path: str, with_token_query: bool = False) -> str:
        if with_token_query and token:
            sep = "&" if ("?" in path) else "?"
            return f"{server_base_url.rstrip('/')}{path}{sep}token={token}"
        return f"{server_base_url.rstrip('/')}{path}"

    print(f"[CLIENT] connecting to {server_base_url} ...")
    print(f"[CLIENT] using crawler script: {crawler_script_path}")

    while True:
        try:
            # 拉取任务
            req = urllib.request.Request(
                _url("/api/next"), headers=_headers(), method="GET"
            )
            try:
                with opener.open(req, timeout=30) as resp:
                    status = resp.getcode()
                    if status == HTTPStatus.NO_CONTENT:
                        time.sleep(poll_interval)
                        continue
                    payload = json.loads(resp.read().decode("utf-8") or "{}")
            except urllib.error.HTTPError as e:
                if e.code == HTTPStatus.NO_CONTENT:
                    time.sleep(poll_interval)
                    continue
                raise
            except urllib.error.URLError as e:
                # 常见：被系统代理转发失败产生的 Bad Gateway / 连接失败
                print(f"[CLIENT] fetch task failed (network): {e}")
                time.sleep(max(5.0, poll_interval))
                continue

            task_id = payload.get("task_id")
            query = payload.get("query")
            top_k = int(payload.get("top_k") or 3)
            proxy = payload.get("proxy")
            filter_year = payload.get("filter_year")

            if not task_id or not query:
                time.sleep(poll_interval)
                continue

            print(f"[CLIENT] got task {task_id}: '{query}' (top_k={top_k})")

            # Execute search with automatic error recovery
            try:
                results = module.simulate_search_api(
                    query, 
                    top_k=top_k, 
                    proxy=proxy, 
                    filter_year=filter_year
                )
                error = None
            except Exception as e:
                results = None
                error = f"client_exec_error: {e}"

            # 回传结果
            result_req = urllib.request.Request(
                _url("/api/result"),
                headers=_headers(),
                data=json.dumps(
                    {
                        "task_id": task_id,
                        "results": results,
                        "error": error,
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                method="POST",
            )
            try:
                with opener.open(result_req, timeout=60) as resp:
                    _ = resp.read()
                if error:
                    print(f"[CLIENT] task {task_id} failed: {error}")
                else:
                    print(
                        f"[CLIENT] task {task_id} done, {len(results or [])} results uploaded"
                    )
            except Exception as e:
                print(f"[CLIENT] upload result failed for task {task_id}: {e}")

        except KeyboardInterrupt:
            print("\n[CLIENT] interrupted, exiting...")
            break
        except Exception as e:
            print(f"[CLIENT] loop error: {e}")
            time.sleep(max(5.0, poll_interval))


# ------------------------------
# CLI
# ------------------------------


def main():
    default_dir = os.path.dirname(os.path.abspath(__file__))
    default_crawler_script = os.path.join(default_dir, "google-web-crawler.py")

    parser = argparse.ArgumentParser(
        description="Remote runner for google-web-crawler: 在服务器与本机之间建立任务分发与结果回传",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # server
    p_server = sub.add_parser("server", help="启动服务器端（任务队列 + 结果收集）")
    p_server.add_argument("--host", default="0.0.0.0")
    p_server.add_argument("--port", type=int, default=8765)
    p_server.add_argument("--token", default=None, help="服务访问令牌，建议设置")
    p_server.add_argument(
        "--output-dir", default=os.path.join(default_dir, "remote_outputs")
    )

    # client
    p_client = sub.add_parser("client", help="在本机运行客户端，使用Chrome执行搜索")
    p_client.add_argument(
        "--server", required=True, help="服务器地址，例如 http://<SERVER_IP>:8765"
    )
    p_client.add_argument("--token", default=None, help="与服务器一致的访问令牌")
    p_client.add_argument(
        "--crawler-script",
        default=default_crawler_script,
        help="本地可执行的 google-web-crawler.py 路径",
    )
    p_client.add_argument("--poll-interval", type=float, default=3.0)
    p_client.add_argument(
        "--no-proxy",
        action="store_true",
        help="禁用客户端对服务器请求使用系统代理(http_proxy/https_proxy)",
    )

    # enqueue (便捷命令)：直接在服务器上添加任务
    p_enq = sub.add_parser(
        "enqueue", help="入队一个任务：本地内存(默认)或通过HTTP提交到远程服务端"
    )
    p_enq.add_argument("--query", required=True)
    p_enq.add_argument("--top-k", type=int, default=3)
    p_enq.add_argument("--proxy", default=None)
    p_enq.add_argument("--filter-year", type=int, default=None, help="Filter results by specific year")
    # 当提供 --server 时，通过HTTP调用远程 /api/enqueue 进行入队
    p_enq.add_argument(
        "--server", default=None, help="远程服务地址，例如 http://127.0.0.1:8765"
    )
    p_enq.add_argument("--token", default=None, help="远程服务访问令牌")
    p_enq.add_argument(
        "--no-proxy",
        action="store_true",
        help="禁用系统代理用于HTTP请求",
    )

    # status / get-result（便捷控制台查看）
    p_status = sub.add_parser("status", help="查看服务器内存中的任务状态")
    p_getres = sub.add_parser("get-result", help="查看某个任务的结果")
    p_getres.add_argument("task_id", help="任务ID")

    args = parser.parse_args()

    if args.cmd == "server":
        os.makedirs(args.output_dir, exist_ok=True)
        run_server(args.host, args.port, args.token, args.output_dir)
        return

    if args.cmd == "client":
        client_loop(
            server_base_url=args.server,
            token=args.token,
            crawler_script_path=args.crawler_script,
            poll_interval=args.poll_interval,
            disable_http_proxy=args.no_proxy,
        )
        return

    # 以下为在同一进程中直接操作内存队列的便捷命令，仅当你就在服务器上执行时有意义
    if args.cmd == "enqueue":
        if args.server:
            import urllib.request

            # 远程HTTP入队
            if args.no_proxy:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            else:
                opener = urllib.request.build_opener()

            url = f"{args.server.rstrip('/')}/api/enqueue"
            headers = {"Content-Type": "application/json"}
            if args.token:
                headers["X-Auth-Token"] = args.token
            payload = {
                "query": args.query,
                "top_k": int(args.top_k),
                "proxy": args.proxy,
                "filter_year": args.filter_year,
            }
            req = urllib.request.Request(
                url,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                method="POST",
            )
            try:
                with opener.open(req, timeout=30) as resp:
                    data = resp.read().decode("utf-8")
                    print(data)
            except Exception as e:
                print(json.dumps({"error": f"enqueue_failed: {e}"}, ensure_ascii=False))
            return
        else:
            # 本地内存入队（仅对当前进程有效，不能影响已运行的server进程）
            task = Task(query=args.query, top_k=args.top_k, proxy=args.proxy, filter_year=args.filter_year)
            task_id = GLOBAL_STORE.enqueue(task)
            print(json.dumps({"task_id": task_id}, ensure_ascii=False))
            return

    if args.cmd == "status":
        print(json.dumps(GLOBAL_STORE.get_status(), ensure_ascii=False, indent=2))
        return

    if args.cmd == "get-result":
        res = GLOBAL_STORE.get_result(args.task_id)
        task = GLOBAL_STORE.get_task(args.task_id)
        if not task:
            print(json.dumps({"error": "task_not_found"}, ensure_ascii=False))
            return
        print(
            json.dumps(
                {
                    "task": {"id": task.id, "status": task.status, "error": task.error},
                    "results": res,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return


if __name__ == "__main__":
    main()


# python google-web-crawler-remote.py server --host 0.0.0.0 --port 1706 --token 1234567890 --output-dir ./remote_outputs
