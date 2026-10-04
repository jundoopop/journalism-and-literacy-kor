"""Prometheus HTTP metrics with bounded route labels, for one threaded worker."""
import time
from flask import g, request, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

registry = CollectorRegistry()
requests_total = Counter("news_http_requests_total", "Completed HTTP requests",
                         ["method", "route", "status"], registry=registry)
duration = Histogram("news_http_request_duration_seconds", "HTTP request duration",
                     ["method", "route"], registry=registry,
                     buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60))


def setup_http_metrics(app):
    @app.before_request
    def start():
        g.http_metric_start = time.perf_counter()

    @app.after_request
    def finish(response):
        if request.path == "/metrics":
            return response
        route = request.url_rule.rule if request.url_rule else "unmatched"
        method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"} else "OTHER"
        requests_total.labels(method, route, str(response.status_code)).inc()
        if hasattr(g, "http_metric_start"):
            duration.labels(method, route).observe(time.perf_counter() - g.http_metric_start)
        return response


def metrics_response():
    return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
