"""Model service: FastAPI wrapper around the trained Predictor.

If an API key is configured (env var MODEL_API_KEY), POST /predict requires the header `X-API-Key: <key>`;
/health and /docs stay open. Without a key (local development) the API is open and /health reports "auth": "off".
"""
import os
import secrets
import threading
from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader

from intrusion.inference import Predictor
from intrusion.playbook import assess
from intrusion.preprocess import Session

API_KEY_HEADER = "X-API-Key"


def create_app(load_predictor: Callable[[], Predictor], api_key: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Store Session MLP API",
        description="Scores a login session for intrusion risk. Use **Authorize** to enter the API key, then try `POST /predict`.",
    )
    lock = threading.Lock()  # sync endpoints run in a threadpool; load the predictor only once
    state: dict = {"predictor": None}
    key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False, description="Shared secret for this API")

    def require_key(provided: str | None = Security(key_header)) -> None:
        if api_key is None:
            return
        # compare_digest takes the same time for any wrong key, so the key cannot be guessed character by character
        if provided is None or not secrets.compare_digest(provided.encode(), api_key.encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid API key")

    def get_predictor() -> Predictor:
        # Caller must hold `lock`. A failed load is not cached, so the next request retries.
        if state["predictor"] is None:
            try:
                state["predictor"] = load_predictor()
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"Model not available: {exc}") from exc
        return state["predictor"]

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")

    @app.get("/health")
    def health() -> dict:
        with lock:
            return {"status": "ok", "model_version": get_predictor().version, "auth": "on" if api_key else "off"}

    @app.post("/predict", dependencies=[Depends(require_key)])
    def predict(session: Session) -> dict:
        with lock:
            result = get_predictor().predict(session)
        return {**result, **assess(session, result["risk"])}

    return app


app = create_app(
    lambda: Predictor.load(Path(os.environ.get("ARTIFACTS_DIR", "artifacts"))),
    api_key=os.environ.get("MODEL_API_KEY") or None,
)
