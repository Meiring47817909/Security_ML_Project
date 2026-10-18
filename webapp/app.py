"""Admin dashboard: live feed of scored sessions, detail view with rule-based actions, manual scoring."""
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from intrusion.inference import Predictor
from intrusion.preprocess import CATEGORIES, ORIGINAL_FEATURES, Session
from webapp.client import ModelClient, ModelUnavailable
from webapp.feed import FeedStore, ScoredSession, SessionFeed

HERE = Path(__file__).parent
RISKS = ("Low", "Medium", "High")
SOURCE_LABELS = {"remote": "Hosted model", "local": "Local fallback"}
FIELD_LABELS = {
    "network_packet_size": "Network packet size (bytes)",
    "protocol_type": "Protocol",
    "login_attempts": "Login attempts",
    "session_duration": "Session duration (s)",
    "encryption_used": "Encryption",
    "ip_reputation_score": "IP reputation score (0-1)",
    "failed_logins": "Failed logins",
    "browser_type": "Browser",
    "unusual_time_access": "Unusual time access",
}


def _risk_filter(risk: str | None) -> str | None:
    return risk if risk in RISKS else None


def create_app(client: ModelClient, feed: SessionFeed | None) -> FastAPI:
    app = FastAPI(title="Store Session Monitor")
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["pct"] = lambda p: f"{p * 100:.1f}%"
    templates.env.filters["hms"] = lambda d: d.strftime("%H:%M:%S")
    store = FeedStore()
    state = {"paused": False, "model_unavailable": False}

    def header_context() -> dict:
        if state["model_unavailable"] or client.last_source is None:
            badge = "Model offline"
        else:
            badge = SOURCE_LABELS.get(client.last_source, "Model offline")
        matches, total = store.agreement()
        return {
            "badge": badge,
            "matches": matches,
            "total": total,
            "show_banner": feed is None or state["model_unavailable"],
            "paused": state["paused"],
        }

    def score(session: Session) -> dict:
        try:
            result = client.predict(session)
        except ModelUnavailable:
            state["model_unavailable"] = True
            raise
        state["model_unavailable"] = False
        return result

    def scored(session_id: str, session: Session, label: int | None, result: dict) -> ScoredSession:
        return ScoredSession(
            session_id, session, label, result["probability"], result["risk"], result["source"],
            datetime.now(), result["pattern"], list(result["actions"]),
        )

    def form_page(request: Request, values: dict, errors: dict, status_code: int, error: str | None = None):
        return templates.TemplateResponse(
            request,
            "new.html",
            {
                **header_context(),
                "fields": ORIGINAL_FEATURES,
                "labels": FIELD_LABELS,
                "categories": {**CATEGORIES, "unusual_time_access": ["0", "1"]},
                "values": values,
                "errors": errors,
                "error": error,
            },
            status_code=status_code,
        )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, risk: str | None = None):
        risk = _risk_filter(risk)
        return templates.TemplateResponse(
            request,
            "index.html",
            {**header_context(), "risk": risk, "risks": RISKS, "items": store.list(risk)},
        )

    @app.get("/feed/next")
    def feed_next(request: Request, risk: str | None = None):
        if feed is None or state["paused"]:
            return Response(status_code=204)
        session_id, session, label = feed.next()
        try:
            result = score(session)
        except ModelUnavailable:
            return Response(status_code=204, headers={"HX-Trigger": "counters"})
        item = scored(session_id, session, label, result)
        store.add(item)
        headers = {"HX-Trigger": "counters"}
        risk = _risk_filter(risk)
        if risk is not None and item.risk != risk:
            return HTMLResponse("", headers=headers)
        return templates.TemplateResponse(request, "_row.html", {"item": item}, headers=headers)

    @app.post("/feed/pause", response_class=HTMLResponse)
    def pause(request: Request):
        state["paused"] = True
        return templates.TemplateResponse(request, "_pause.html", {"paused": True})

    @app.post("/feed/resume", response_class=HTMLResponse)
    def resume(request: Request):
        state["paused"] = False
        return templates.TemplateResponse(request, "_pause.html", {"paused": False})

    @app.get("/counters", response_class=HTMLResponse)
    def counters(request: Request):
        return templates.TemplateResponse(request, "_counters.html", header_context())

    @app.get("/sessions/new", response_class=HTMLResponse)
    def new_session(request: Request):
        values = {k: "" for k in ORIGINAL_FEATURES}
        return form_page(request, values, {}, 200)

    @app.post("/sessions")
    async def create_session(request: Request):
        form = await request.form()
        values = {k: str(form.get(k, "")) for k in ORIGINAL_FEATURES}
        try:
            session = Session(**values)
        except ValidationError as exc:
            errors = {str(e["loc"][0]): e["msg"] for e in exc.errors() if e["loc"]}
            return form_page(request, values, errors, 422)
        try:
            result = await run_in_threadpool(score, session)
        except ModelUnavailable:
            return form_page(request, values, {}, 503, error="Model unavailable: the session could not be scored.")
        item = scored(store.next_manual_id(), session, None, result)
        store.add(item)
        return RedirectResponse(f"/sessions/{item.id}", status_code=303)

    @app.get("/sessions/{session_id}", response_class=HTMLResponse)
    def detail(request: Request, session_id: str):
        item = store.get(session_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Unknown session")
        return templates.TemplateResponse(
            request,
            "detail.html",
            {
                **header_context(),
                "item": item,
                "features": [(FIELD_LABELS[k], getattr(item.session, k)) for k in ORIGINAL_FEATURES],
            },
        )

    return app


def _build_default_app() -> FastAPI:
    artifacts = Path(os.environ.get("ARTIFACTS_DIR", "artifacts"))
    client = ModelClient(os.environ.get("MODEL_API_URL") or None, lambda: Predictor.load(artifacts))
    csv = artifacts / "test_sessions.csv"
    return create_app(client, SessionFeed.from_csv(csv) if csv.exists() else None)


app = _build_default_app()
