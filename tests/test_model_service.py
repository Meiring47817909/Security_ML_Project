from conftest import VALID_SESSION
from fastapi.testclient import TestClient

from model_service.app import create_app


class StubPredictor:
    version = "stub"

    def predict(self, session):
        return {"probability": 0.9, "risk": "High", "prediction": 1}


def make_client(loader=StubPredictor):
    return TestClient(create_app(loader))


def test_health():
    assert make_client().get("/health").json() == {"status": "ok", "model_version": "stub"}


def test_predict_includes_rule_based_playbook():
    r = make_client().post("/predict", json={**VALID_SESSION, "failed_logins": 4})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"probability", "risk", "prediction", "pattern", "actions"}
    assert body["pattern"] == "Brute force / credential stuffing"


def test_explain_endpoint_removed():
    assert make_client().post("/explain", json=VALID_SESSION).status_code == 404


def test_invalid_session_422():
    r = make_client().post("/predict", json={**VALID_SESSION, "ip_reputation_score": 2})
    assert r.status_code == 422


def test_missing_model_503_and_retry():
    calls = []

    def loader():
        calls.append(1)
        if len(calls) == 1:
            raise FileNotFoundError("no artifacts")
        return StubPredictor()

    c = make_client(loader)
    r = c.post("/predict", json=VALID_SESSION)
    assert r.status_code == 503
    assert r.json() == {"detail": "Model not available: no artifacts"}
    assert c.get("/health").status_code == 200  # failure was not cached
    assert c.post("/predict", json=VALID_SESSION).status_code == 200
    assert len(calls) == 2  # loaded once after the retry
