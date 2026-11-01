"""Synthetic benchmark only: real API/parsing/database, fake external I/O.

Never imported by the production Dockerfile or server. No real model/news calls.
"""
import os
import time
from pathlib import Path

os.environ["CACHE_ENABLED"] = "False"
os.environ["ENABLE_CACHE"] = "False"
import server
import crawler_unified
from llm.base import AnalysisResult
from llm.factory import LLMFactory
from config import settings

TEXT = "지역 예산의 사용 근거를 확인해야 한다."
HTML = "<html><title>Fixture article</title><body><article><p>" + TEXT * 100 + "</p></article></body></html>"
settings.enable_cache = False
server.crawler_service._crawler = {
    "fetch": lambda url: HTML,
    "parse": crawler_unified.parse_article,
}


class FixtureProvider:
    def __init__(self, name):
        self.name = name

    def analyze_article(self, article_text, system_prompt):
        marker = os.environ.get("BENCHMARK_STARTED_FILE")
        if marker:
            Path(marker).touch()
        time.sleep(float(os.environ.get("FIXTURE_DELAY_SECONDS", "0.05")))
        return AnalysisResult({TEXT: "근거를 검토하는 문장"}, self.name, "synthetic")


LLMFactory.create = staticmethod(lambda provider=None, **kw: FixtureProvider(provider))
app = server.app
