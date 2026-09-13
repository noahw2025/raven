FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN addgroup --system raven && adduser --system --ingroup raven raven
COPY requirements.txt .
RUN pip install --requirement requirements.txt
COPY app ./app
COPY tests ./tests
RUN chown -R raven:raven /app
USER raven
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
