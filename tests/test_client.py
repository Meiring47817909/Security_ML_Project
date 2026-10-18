import httpx
import pytest
from conftest import VALID_SESSION

from intrusion.preprocess import Session
from webapp.client import ModelClient, ModelUnavailable

SESSION = Session(**VALID_SESSION)
PRED = {"probability": 0.9, "risk": "High", "prediction": 1}


class StubPredictor:
    def predict(self, session):
        return dict(PRED)


def make_loader(counter):
    def loader():
        counter.append(1)
        return StubPredictor()

    return loader


def http_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_uses_remote_when_ok():
    calls = []

    def handler(request):
        assert request.url.path == "/predict"
        return httpx.Response(200, json={"probability": 0.1, "risk": "Low", "prediction": 0})

    c = ModelClient("http://model", make_loader(calls), http=http_with(handler))
    out = c.predict(SESSION)
    assert out["source"] == "remote" and not calls
    assert c.last_source == "remote"


def test_remote_passes_through_pattern():
    body = {**PRED, "pattern": "p", "actions": ["a"]}
    c = ModelClient("http://model", make_loader([]), http=http_with(lambda r: httpx.Response(200, json=body)))
    out = c.predict(SESSION)
    assert out["pattern"] == "p" and out["source"] == "remote"


def test_falls_back_on_connection_error():
    def handler(request):
        raise httpx.ConnectError("down")

    c = ModelClient("http://model", make_loader([]), http=http_with(handler))
    assert c.predict(SESSION)["source"] == "local"
    assert c.last_source == "local"


@pytest.mark.parametrize("resp", [httpx.Response(500), httpx.Response(200, content=b"not json")])
def test_falls_back_on_server_error(resp):
    c = ModelClient("http://model", make_loader([]), http=http_with(lambda r: resp))
    assert c.predict(SESSION)["source"] == "local"


def test_remote_failure_logs_warning(caplog):
    def handler(request):
        raise httpx.ConnectError("down")

    c = ModelClient("http://model", make_loader([]), http=http_with(handler))
    with caplog.at_level("WARNING", logger="webapp.client"):
        c.predict(SESSION)
    assert any("remote predict failed" in r.getMessage() for r in caplog.records)


def test_no_remote_url_uses_local(caplog):
    with caplog.at_level("WARNING", logger="webapp.client"):
        assert ModelClient(None, make_loader([])).predict(SESSION)["source"] == "local"
    assert not caplog.records


def test_local_loader_called_once():
    calls = []
    c = ModelClient(None, make_loader(calls))
    c.predict(SESSION)
    c.predict(SESSION)
    assert len(calls) == 1


def test_raises_when_both_fail():
    def loader():
        raise FileNotFoundError("no artifacts")

    def handler(request):
        raise httpx.ConnectError("down")

    c = ModelClient("http://model", loader, http=http_with(handler))
    with pytest.raises(ModelUnavailable):
        c.predict(SESSION)


def test_local_predict_includes_rule_based_playbook():
    out = ModelClient(None, make_loader([])).predict(Session(**{**VALID_SESSION, "ip_reputation_score": 0.9}))
    assert out["pattern"] == "Known-bad source" and out["source"] == "local"
    assert set(out) == {"probability", "risk", "prediction", "pattern", "actions", "source"}


def test_client_has_no_explain():
    assert not hasattr(ModelClient(None, make_loader([])), "explain")


def test_concurrent_first_requests_load_once():
    import threading
    import time

    calls = []

    def slow_loader():
        calls.append(1)
        time.sleep(0.05)
        return StubPredictor()

    c = ModelClient(None, slow_loader)
    threads = [threading.Thread(target=c.predict, args=(SESSION,)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
