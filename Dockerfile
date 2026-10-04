FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt \
    && useradd --create-home appuser
COPY scripts ./scripts
COPY gunicorn.conf.py .
RUN mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser
ENV BIND=0.0.0.0:5001 FLASK_DEBUG=False
EXPOSE 5001
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/healthz', timeout=2)"
CMD ["gunicorn", "--pythonpath", "scripts", "--config", "gunicorn.conf.py", "server:app"]
