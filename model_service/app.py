"""Model service: FastAPI wrapper around the trained Predictor."""
import os
import threading
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException

from intrusion.inference import Predictor
from intrusion.playbook import assess
from intrusion.preprocess import Session


def create_app(load_predictor: Callable[[], Predictor]) -> FastAPI:
    app = FastAPI(title="Intrusion model service")
    lock = threading.Lock()  # sync endpoints run in a threadpool; load the predictor only once
    state: dict = {"predictor": None}

    def get_predictor() -> Predictor:
        # Caller must hold `lock`. A failed load is not cached, so the next request retries.
        if state["predictor"] is None:
            try:
                state["predictor"] = load_predictor()
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"Model not available: {exc}") from exc
        return state["predictor"]

    @app.get("/health")
    def health() -> dict:
        with lock:
            return {"status": "ok", "model_version": get_predictor().version}

    @app.post("/predict")
    def predict(session: Session) -> dict:
        with lock:
            result = get_predictor().predict(session)
        return {**result, **assess(session, result["risk"])}

    return app


app = create_app(lambda: Predictor.load(Path(os.environ.get("ARTIFACTS_DIR", "artifacts"))))
