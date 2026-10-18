"""Artifact I/O, risk levels and prediction."""
import json
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import torch

from intrusion.model import MLP
from intrusion.preprocess import Session, to_frame

THRESHOLD = 0.5


def risk_level(p: float) -> Literal["Low", "Medium", "High"]:
    if p < 0.4:
        return "Low"
    if p < 0.7:
        return "Medium"
    return "High"


def save_artifacts(out_dir: Path, model: MLP, preprocessor, version: str) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out_dir / "mlp.pt")
    joblib.dump(preprocessor, out_dir / "preprocess.joblib")
    meta = {"version": version, "in_features": 17, "threshold": THRESHOLD}
    (out_dir / "model_meta.json").write_text(json.dumps(meta), encoding="utf-8")


class Predictor:
    def __init__(self, model: MLP, preprocessor, version: str):
        self.model = model.eval()
        self.preprocessor = preprocessor
        self.version = version

    @classmethod
    def load(cls, artifacts_dir: Path | str) -> "Predictor":
        d = Path(artifacts_dir)
        meta = json.loads((d / "model_meta.json").read_text(encoding="utf-8"))
        model = MLP(in_features=meta["in_features"])
        model.load_state_dict(torch.load(d / "mlp.pt", map_location="cpu"))
        return cls(model, joblib.load(d / "preprocess.joblib"), meta["version"])

    def predict(self, session: Session) -> dict:
        x = np.asarray(self.preprocessor.transform(to_frame([session])), dtype=np.float32)
        with torch.no_grad():
            p = float(torch.sigmoid(self.model(torch.as_tensor(x))).reshape(-1)[0])
        return {"probability": p, "risk": risk_level(p), "prediction": int(p >= THRESHOLD)}
