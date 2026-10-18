"""Rule-based threat pattern and preventive-action playbook.

The rules look at the session's own values, not at the model. They mirror the
patterns visible in the data: many failed logins or login attempts, a poor IP
reputation, or an unidentified browser.
"""
from intrusion.preprocess import Session

FAILED_LOGINS_MIN = 3
LOGIN_ATTEMPTS_MIN = 7
BAD_REPUTATION_ABOVE = 0.6

PLAYBOOK = {
    "brute_force": {
        "pattern": "Brute force / credential stuffing",
        "actions": [
            "Temporary account lockout",
            "Enforce MFA",
            "CAPTCHA after repeated failures",
            "Alert account owner",
        ],
    },
    "bad_source": {
        "pattern": "Known-bad source",
        "actions": [
            "Block or rate-limit the IP",
            "Add a WAF rule",
            "Check other sessions from that IP",
        ],
    },
    "bot": {
        "pattern": "Automated bot / scripted client",
        "actions": [
            "Bot detection / challenge",
            "Require JavaScript-capable client",
            "Rate-limit",
        ],
    },
    "anomalous": {
        "pattern": "Anomalous session",
        "actions": ["Manual review", "Step-up authentication"],
    },
}


def _entry(key: str) -> dict:
    return {"pattern": PLAYBOOK[key]["pattern"], "actions": list(PLAYBOOK[key]["actions"])}


def assess(session: Session, risk: str) -> dict:
    """Return {"pattern", "actions"} for a scored session, checking rules in priority order."""
    if risk == "Low":
        return {"pattern": "None", "actions": ["No action"]}
    if session.failed_logins >= FAILED_LOGINS_MIN or session.login_attempts >= LOGIN_ATTEMPTS_MIN:
        return _entry("brute_force")
    if session.ip_reputation_score > BAD_REPUTATION_ABOVE:
        return _entry("bad_source")
    if session.browser_type == "Unknown":
        return _entry("bot")
    return _entry("anomalous")
