
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "python backend/migrate.py && exec gunicorn backend.blockchain_api_server:app --bind 0.0.0.0:${PORT}"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz').read()"
