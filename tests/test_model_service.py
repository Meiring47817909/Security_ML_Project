from conftest import VALID_SESSION
from fastapi.testclient import TestClient

from model_service.app import create_app


class StubPredictor:
    version = "stub"

    def predict(self, session):
        return {"probability": 0.9, "risk": "High", "prediction": 1}


KEY = "test-key-123"


def make_client(loader=StubPredictor, api_key=None):
    return TestClient(create_app(loader, api_key=api_key))


def test_health():
    assert make_client().get("/health").json() == {"status": "ok", "model_version": "stub", "auth": "off"}


def test_root_redirects_to_docs():
    r = make_client().get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_auth_on_requires_key():
    c = make_client(api_key=KEY)
    assert c.post("/predict", json=VALID_SESSION).status_code == 401
    assert c.post("/predict", json=VALID_SESSION, headers={"X-API-Key": "wrong"}).status_code == 401
    r = c.post("/predict", json=VALID_SESSION, headers={"X-API-Key": KEY})
    assert r.status_code == 200 and "probability" in r.json()


def test_auth_on_keeps_health_and_docs_open():
    c = make_client(api_key=KEY)
    assert c.get("/health").json()["auth"] == "on"
    assert c.get("/docs").status_code == 200


def test_auth_checked_before_validation():
    r = make_client(api_key=KEY).post("/predict", json={"junk": 1})
    assert r.status_code == 401  # no key -> rejected without revealing schema errors


def test_openapi_documents_api_key():
    spec = make_client(api_key=KEY).get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    assert any(v.get("type") == "apiKey" and v.get("name") == "X-API-Key" for v in schemes.values())


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
