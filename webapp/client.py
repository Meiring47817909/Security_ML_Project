"""Model client: remote model service first, local predictor as fallback."""
import logging
import threading
from collections.abc import Callable

import httpx

from intrusion.playbook import assess
from intrusion.preprocess import Session

logger = logging.getLogger(__name__)


class ModelUnavailable(Exception):
    """Neither the remote service nor the local predictor could answer."""


class ModelClient:
    def __init__(
        self,
        remote_url: str | None,
        local_loader: Callable,
        timeout: float = 10.0,
        http: httpx.Client | None = None,
        api_key: str | None = None,
    ):
        self._remote_url = remote_url.rstrip("/") if remote_url else None
        self._headers = {"X-API-Key": api_key} if api_key else {}
        self._local_loader = local_loader
        self._http = http or httpx.Client(timeout=timeout)
        self._predictor = None
        self._lock = threading.Lock()
        self.last_source: str | None = None

    def predict(self, session: Session) -> dict:
        """Score a session: probability, risk, prediction, rule-based pattern/actions, and source."""
        out = self._remote(session, "predict")
        if out is not None:
            source = "remote"
        else:
            out = self._local(session)
            source = "local"
        self.last_source = source
        return {**out, "source": source}

    def _remote(self, session: Session, op: str) -> dict | None:
        if not self._remote_url:
            return None
        try:
            resp = self._http.post(f"{self._remote_url}/{op}", json=session.model_dump(), headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError(f"expected a JSON object, got {type(data).__name__}")
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("remote %s failed: %r; using local model", op, exc)
            return None
        return data

    def _local(self, session: Session) -> dict:
        try:
            with self._lock:
                if self._predictor is None:
                    self._predictor = self._local_loader()
                out = self._predictor.predict(session)
            return {**out, **assess(session, out["risk"])}
        except Exception as exc:
            raise ModelUnavailable(str(exc)) from exc
