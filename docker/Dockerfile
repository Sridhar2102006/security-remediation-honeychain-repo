
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask cryptography pytest
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
EXPOSE 8000
CMD ["python", "-m", "backend.blockchain_api_server"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()"
