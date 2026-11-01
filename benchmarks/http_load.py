"""Reproducible local HTTP experiment; no live upstreams, no production SLO claim."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import hashlib
from importlib.metadata import version
import math
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
BODY = json.dumps({"url": "https://www.hani.co.kr/fixture",
                   "providers": ["gemini", "mistral"]}).encode()


def request_once(base):
    start = time.perf_counter()
    try:
        req = urllib.request.Request(base + "/analyze_consensus", data=BODY,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.load(response)
            valid = (data.get("success") is True and data.get("count") == 1
                     and data.get("total_providers") == 2
                     and len(data.get("successful_providers", [])) == 2)
            status = response.status if valid else "invalid_body"
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception as exc:
        status = type(exc).__name__
    return {"latency_ms": (time.perf_counter() - start) * 1000, "status": status}


def launch(directory, threads, delay=.05):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, BIND=f"127.0.0.1:{port}", HTTP_THREADS=str(threads),
               DATABASE_PATH=str(directory / "analytics.db"), LOG_DIR=str(directory / "logs"),
               FIXTURE_DELAY_SECONDS=str(delay), BENCHMARK_STARTED_FILE=str(directory / "started"),
               LOG_LEVEL="WARNING", CACHE_ENABLED="False", ENABLE_CACHE="False")
    log = open(directory / "server.log", "w")
    proc = subprocess.Popen([sys.executable, "-m", "gunicorn", "--pythonpath", "scripts",
                             "--config", "gunicorn.conf.py", "benchmarks.fixture_app:app"],
                            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=.5) as response:
                if response.status == 200:
                    return proc, base
        except (OSError, urllib.error.URLError):
            time.sleep(.1)
        if proc.poll() is not None:
            break
    if proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=10)
    raise RuntimeError((directory / "server.log").read_text()[-4000:])


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.requests < 1 or args.repeats < 1:
        parser.error("requests and repeats must be positive")
    sources = list((ROOT / 'scripts').rglob('*.py')) + list((ROOT / 'benchmarks').glob('*.py')) + [ROOT / 'gunicorn.conf.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    report = {"source_sha256": hashes,
              "dependencies": {name: version(name) for name in ('flask', 'gunicorn', 'sqlalchemy', 'pydantic', 'prometheus-client')},
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": platform.python_version(),
              "cpu_count": os.cpu_count(), "fixture": "2 parallel fake providers, 50ms each",
              "scope": "real local HTTP, parser, consensus, SQLite; no live LLM/news/Redis",
              "baseline": "same repaired code, 1 HTTP thread; not the broken original app",
              "runs": []}
    for threads in (1, 8):
        with tempfile.TemporaryDirectory(prefix="news-load-") as temp:
            proc, base = launch(Path(temp), threads)
            try:
                for _ in range(3):
                    assert request_once(base)["status"] == 200
                for concurrency in (1, 8):
                    for repeat in range(args.repeats):
                        start = time.perf_counter()
                        with ThreadPoolExecutor(max_workers=concurrency) as executor:
                            samples = list(executor.map(lambda _: request_once(base), range(args.requests)))
                        elapsed = time.perf_counter() - start
                        latencies = sorted(row["latency_ms"] for row in samples)
                        run = {"threads": threads, "clients": concurrency, "repeat": repeat + 1,
                               "requests": len(samples), "errors": sum(s["status"] != 200 for s in samples),
                               "elapsed_s": elapsed, "throughput_rps": len(samples) / elapsed,
                               "p50_ms": latencies[math.ceil(len(samples) * .50) - 1],
                               "p95_ms": latencies[math.ceil(len(samples) * .95) - 1],
                               "p99_ms": latencies[math.ceil(len(samples) * .99) - 1],
                               "samples": samples}
                        report["runs"].append(run)
                        print(json.dumps({k: v for k, v in run.items() if k != "samples"}), flush=True)
            finally:
                stop(proc)
    with tempfile.TemporaryDirectory(prefix="news-shutdown-") as temp:
        directory = Path(temp)
        proc, base = launch(directory, 8, delay=1)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(request_once, base)
                deadline = time.monotonic() + 5
                while not (directory / "started").exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                assert (directory / "started").exists(), "Request never entered provider"
                proc.send_signal(signal.SIGTERM)
                result = future.result(timeout=15)
                code = proc.wait(timeout=15)
                report["graceful_shutdown"] = {"inflight_request": result, "exit_code": code,
                                                "passed": result["status"] == 200 and code == 0}
        finally:
            stop(proc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    if any(r["errors"] for r in report["runs"]) or not report["graceful_shutdown"]["passed"]:
        raise SystemExit("Experiment failed; inspect the report")


if __name__ == "__main__":
    main()
