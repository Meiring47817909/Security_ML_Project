# Docker image for the Store Session MLP API, built from the repository root (used by Render, see render.yaml).
# Same runtime as deploy/hf_space/Dockerfile: CPU-only PyTorch and the pinned API requirements.
FROM python:3.13-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ARTIFACTS_DIR=/home/user/app/artifacts
WORKDIR /home/user/app

# CPU-only PyTorch (no GPU on the host, and the CPU build is far smaller)
RUN pip install --no-cache-dir --user torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user deploy/hf_space/requirements.txt requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user intrusion intrusion
COPY --chown=user model_service model_service
COPY --chown=user artifacts/mlp.pt artifacts/preprocess.joblib artifacts/model_meta.json artifacts/

EXPOSE 7860
# Render sets PORT; locally it defaults to 7860
CMD ["sh", "-c", "uvicorn model_service.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
