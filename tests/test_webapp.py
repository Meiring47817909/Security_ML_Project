import pandas as pd
from conftest import VALID_SESSION
from fastapi.testclient import TestClient

from webapp.app import create_app
from webapp.client import ModelUnavailable
from webapp.feed import SessionFeed

VALID_FORM = {k: str(v) for k, v in VALID_SESSION.items()}


class StubClient:
    def __init__(self, probability=0.2, risk="Low", fail=False):
        self.probability = probability
        self.risk = risk
        self.fail = fail
        self.last_source = None

    def predict(self, session):
        if self.fail:
            raise ModelUnavailable("down")
        self.last_source = "remote"
        return {
            "probability": self.probability,
            "risk": self.risk,
            "prediction": int(self.probability >= 0.5),
            "pattern": "Brute force / credential stuffing",
            "actions": ["Temporary account lockout", "Enforce MFA"],
            "source": "remote",
        }


def make_feed(n=3):
    rows = [{"session_id": f"SID_{i:05d}", **VALID_SESSION, "attack_detected": i % 2} for i in range(n)]
    return SessionFeed(pd.DataFrame(rows))


def make_client(stub=None, feed="default"):
    stub = stub or StubClient()
    return TestClient(create_app(stub, make_feed() if feed == "default" else feed))


def test_index_renders():
    r = make_client().get("/")
    assert r.status_code == 200 and "Store Session Monitor" in r.text
    assert 'hx-trigger="every 3s"' in r.text


def test_feed_next_returns_row_and_stores():
    c = make_client()
    r = c.get("/feed/next")
    assert r.status_code == 200 and "SID_00000" in r.text
    assert r.headers["HX-Trigger"] == "counters"
    assert "20.0%" in r.text and "Low" in r.text
    assert c.get("/sessions/SID_00000").status_code == 200


def test_pause_returns_204():
    c = make_client()
    r = c.post("/feed/pause")
    assert "Resume" in r.text
    assert c.get("/feed/next").status_code == 204
    assert "Pause" in c.post("/feed/resume").text
    assert c.get("/feed/next").status_code == 200


def test_risk_filter_hides_nonmatching():
    c = make_client(StubClient(risk="Low"))
    r = c.get("/feed/next?risk=High")
    assert r.status_code == 200 and r.text.strip() == ""
    assert c.get("/sessions/SID_00000").status_code == 200  # still stored


def test_counters_show_agreement_and_source():
    c = make_client()
    assert "Model offline" in c.get("/counters").text
    c.get("/feed/next")  # SID_00000, label 0, p=0.2 -> match
    c.get("/feed/next")  # SID_00001, label 1, p=0.2 -> mismatch
    r = c.get("/counters")
    assert "1 / 2" in r.text and "Hosted model" in r.text


def test_manual_entry_valid_redirects():
    c = make_client()
    r = c.post("/sessions", data=VALID_FORM, follow_redirects=False)
    assert r.status_code == 303 and "/sessions/MAN_00001" in r.headers["location"]


def test_manual_entry_invalid_422():
    c = make_client()
    r = c.post("/sessions", data={**VALID_FORM, "ip_reputation_score": "5"})
    assert r.status_code == 422 and "ip_reputation_score" in r.text
    assert 'value="5"' in r.text


def test_new_form_renders():
    r = make_client().get("/sessions/new")
    assert r.status_code == 200
    for name in VALID_SESSION:
        assert f'name="{name}"' in r.text


def test_detail_shows_pattern_and_actions_without_xai():
    c = make_client()
    c.post("/sessions", data=VALID_FORM)
    r = c.get("/sessions/MAN_00001")
    assert r.status_code == 200
    assert "Brute force" in r.text and "Enforce MFA" in r.text
    assert "fixed rules on the session" in r.text and "not from the model" in r.text
    assert "SHAP" not in r.text and "contribution" not in r.text


def test_detail_uses_stored_result_even_if_model_later_fails():
    stub = StubClient()
    c = make_client(stub)
    c.get("/feed/next")
    stub.fail = True
    r = c.get("/sessions/SID_00000")
    assert r.status_code == 200 and "Brute force" in r.text


def test_unknown_session_404():
    assert make_client().get("/sessions/NOPE").status_code == 404


def test_banner_when_no_feed():
    c = make_client(feed=None)
    assert "No trained model found" in c.get("/").text
    assert c.get("/feed/next").status_code == 204


def test_model_unavailable_is_handled():
    stub = StubClient(fail=True)
    c = make_client(stub)
    assert c.get("/feed/next").status_code == 204
    page = c.get("/").text
    assert "No trained model found" in page and "Model offline" in page
    r = c.post("/sessions", data=VALID_FORM)
    assert r.status_code == 503 and "Model unavailable" in r.text
    stub.fail = False
    assert c.get("/feed/next").status_code == 200
    assert "No trained model found" not in c.get("/").text
