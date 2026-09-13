FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-dev build-essential ffmpeg sox libsox-fmt-all espeak-ng libespeak-ng1 && rm -rf /var/lib/apt/lists/*
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel numpy
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /opt/kokoro && python3 -c "import urllib.request; base='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'; urllib.request.urlretrieve(base+'kokoro-v1.0.onnx','/opt/kokoro/kokoro-v1.0.onnx'); urllib.request.urlretrieve(base+'voices-v1.0.bin','/opt/kokoro/voices-v1.0.bin')"
COPY service.py parakeet_stream.py ./
RUN mkdir -p /models/huggingface /models/runtime-tmp && chmod -R a+rX /service /opt/kokoro
# Keep the stable UID used by the existing named model volume so upgrades do
# not silently lose write access to downloaded models.
USER 100
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=5 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health')"
CMD ["python3","-m","uvicorn","service:app","--host","0.0.0.0","--port","8090"]
