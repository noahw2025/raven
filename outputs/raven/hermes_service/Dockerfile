FROM python:3.11.13-slim-bookworm
WORKDIR /hermes
COPY work/hermes-agent /hermes
RUN pip install --no-cache-dir -e . fastapi==0.115.12 uvicorn==0.34.2
COPY outputs/raven/hermes_service/service.py /hermes/raven_service.py
RUN useradd --create-home worker
USER worker
ENV HERMES_HOME=/tmp/hermes PYTHONUNBUFFERED=1
CMD ["uvicorn", "raven_service:app", "--host", "0.0.0.0", "--port", "8092"]
