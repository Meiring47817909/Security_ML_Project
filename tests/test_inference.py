import json

import pytest
from conftest import VALID_SESSION

from intrusion.inference import Predictor, risk_level
from intrusion.preprocess import Session


@pytest.mark.parametrize("p,risk", [(0.0, "Low"), (0.399, "Low"), (0.4, "Medium"), (0.699, "Medium"), (0.7, "High"), (1.0, "High")])
def test_risk_level(p, risk):
    assert risk_level(p) == risk


def test_load_and_predict(artifacts_dir):
    pr = Predictor.load(artifacts_dir)
    out = pr.predict(Session(**VALID_SESSION))
    assert 0 <= out["probability"] <= 1 and out["prediction"] == int(out["probability"] >= 0.5)
    assert out["risk"] == risk_level(out["probability"]) and pr.version == "test"
    json.dumps(out)  # plain Python types only


def test_predict_extreme_but_valid_values(artifacts_dir):
    s = Session(**{**VALID_SESSION, "login_attempts": 80, "failed_logins": 100, "network_packet_size": 60000, "session_duration": 1e6})
    assert 0 <= Predictor.load(artifacts_dir).predict(s)["probability"] <= 1


def test_artifacts_have_no_shap_background(artifacts_dir):
    assert sorted(p.name for p in artifacts_dir.iterdir()) == ["mlp.pt", "model_meta.json", "preprocess.joblib"]
    assert not hasattr(Predictor.load(artifacts_dir), "explain")
