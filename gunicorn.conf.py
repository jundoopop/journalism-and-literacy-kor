"""One process keeps SQLite and in-memory metrics easy to reason about."""
import os

bind = os.getenv("BIND", "127.0.0.1:5001")
workers = 1
worker_class = "gthread"
threads = int(os.getenv("HTTP_THREADS", "8"))
timeout = 90
graceful_timeout = 90
keepalive = 2
backlog = 128
accesslog = "-"
errorlog = "-"
capture_output = True
preload_app = False
