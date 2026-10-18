# Hugging Face Docker Space for the Store Session MLP API.
# Built from ML_Project_New by scripts/build_hf_space.py; the API listens on port 7860 as Spaces require.
FROM python:3.13-slim

# Spaces run containers as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ARTIFACTS_DIR=/home/user/app/artifacts
WORKDIR /home/user/app

# CPU-only PyTorch (free Spaces have no GPU, and the CPU build is far smaller)
RUN pip install --no-cache-dir --user torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
# Hosts that assign a port (e.g. Render) set PORT; otherwise use 7860 (Hugging Face)
CMD ["sh", "-c", "uvicorn model_service.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
