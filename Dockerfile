FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/piishield/.cache/huggingface

WORKDIR /app

# Install the CPU-only wheel explicitly; the requirements pin the same version.
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.11.0
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin piishield
COPY deploy ./deploy

# Cache both GLiNER and its base tokenizer before copying app source so UI/API edits reuse this layer.
RUN python -m deploy.download_model \
    && chown -R piishield:piishield /home/piishield/.cache/huggingface

COPY --chown=piishield:piishield . .

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

USER piishield
EXPOSE 7860
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860} --no-access-log"]
