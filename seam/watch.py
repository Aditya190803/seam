from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .indexer import index_repo, index_status


class HealthState:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.last_indexed_at: str | None = None
        self.last_error: str | None = None
        self.indexing = False


class SeamEventHandler(FileSystemEventHandler):
    def __init__(self, trigger) -> None:  # type: ignore[no-untyped-def]
        self.trigger = trigger

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self.trigger()


def start_health_server(state: HealthState, *, host: str = "127.0.0.1", port: int = 7731) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib API
            if self.path != "/health":
                self.send_response(404)
                self.end_headers()
                return
            payload = {
                "ok": state.last_error is None,
                "indexing": state.indexing,
                "started_at": state.started_at,
                "last_indexed_at": state.last_indexed_at,
                "last_error": state.last_error,
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200 if state.last_error is None else 500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib API
            return

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def watch_repo(path: Path, *, debounce_seconds: float = 1.0, health_port: int = 7731) -> None:
    repo_path = path.expanduser().resolve()
    state = HealthState()
    start_health_server(state, port=health_port)

    pending = threading.Event()
    stopped = threading.Event()

    def request_index() -> None:
        pending.set()

    def worker() -> None:
        while not stopped.is_set():
            pending.wait(timeout=0.5)
            if not pending.is_set():
                continue
            time.sleep(debounce_seconds)
            pending.clear()
            try:
                state.indexing = True
                stats = index_repo(repo_path)
                state.last_indexed_at = stats.last_indexed_at
                state.last_error = None
            except Exception as exc:  # pragma: no cover - long running daemon path
                state.last_error = str(exc)
            finally:
                state.indexing = False

    index_repo(repo_path)
    status = index_status(repo_path)
    state.last_indexed_at = status.last_indexed_at

    observer = Observer()
    observer.schedule(SeamEventHandler(request_index), str(repo_path), recursive=True)
    observer.start()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stopped.set()
        observer.stop()
    finally:
        observer.join(timeout=5)
