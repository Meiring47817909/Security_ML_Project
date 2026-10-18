"""Tests for the rule-based threat pattern and action playbook."""
import pytest

from conftest import VALID_SESSION
from intrusion.playbook import PLAYBOOK, assess
from intrusion.preprocess import Session


def S(**kw):
    """Create Session: merge kw into VALID_SESSION, return Session instance."""
    return Session(**{**VALID_SESSION, **kw})


def test_low_risk_no_action_even_if_rules_match():
    assert assess(S(failed_logins=5), "Low") == {"pattern": "None", "actions": ["No action"]}


@pytest.mark.parametrize("kw", [{"failed_logins": 3}, {"login_attempts": 7}, {"failed_logins": 5, "login_attempts": 9}])
def test_brute_force(kw):
    out = assess(S(**kw), "High")
    assert out == {"pattern": "Brute force / credential stuffing", "actions": PLAYBOOK["brute_force"]["actions"]}


@pytest.mark.parametrize("kw", [{"failed_logins": 2}, {"login_attempts": 6}])
def test_just_below_brute_force_thresholds(kw):
    assert assess(S(**kw), "Medium")["pattern"] == "Anomalous session"


def test_bad_source_threshold_is_strictly_above_0_6():
    assert assess(S(ip_reputation_score=0.61), "High")["pattern"] == "Known-bad source"
    assert assess(S(ip_reputation_score=0.6), "Medium")["pattern"] == "Anomalous session"


def test_bot_on_unknown_browser():
    out = assess(S(browser_type="Unknown"), "Medium")
    assert out == {"pattern": "Automated bot / scripted client", "actions": PLAYBOOK["bot"]["actions"]}


def test_priority_brute_force_before_bad_source_before_bot():
    assert assess(S(failed_logins=4, ip_reputation_score=0.9, browser_type="Unknown"), "High")["pattern"].startswith("Brute force")
    assert assess(S(ip_reputation_score=0.9, browser_type="Unknown"), "High")["pattern"] == "Known-bad source"


def test_anomalous_when_no_rule_matches():
    out = assess(S(), "Medium")
    assert out == {"pattern": "Anomalous session", "actions": ["Manual review", "Step-up authentication"]}


def test_returned_actions_are_a_copy():
    assess(S(failed_logins=4), "High")["actions"].append("x")
    assert "x" not in PLAYBOOK["brute_force"]["actions"]
