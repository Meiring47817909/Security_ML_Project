from datetime import datetime

import pandas as pd
from conftest import VALID_SESSION

from intrusion.preprocess import Session
from webapp.feed import FeedStore, ScoredSession, SessionFeed


def make_df(n=3):
    rows = [{"session_id": f"SID_{i}", **VALID_SESSION, "attack_detected": i % 2} for i in range(n)]
    return pd.DataFrame(rows)


def item(id, p, label, risk="Low"):
    return ScoredSession(id, Session(**VALID_SESSION), label, p, risk, "local", datetime.now(), "None", ["No action"])


def test_feed_wraps_around():
    f = SessionFeed(make_df(3))
    ids = [f.next()[0] for _ in range(4)]
    assert ids[3] == ids[0]
    sid, session, label = SessionFeed(make_df(3)).next()
    assert isinstance(session, Session) and label == 0


def test_from_csv(tmp_path):
    path = tmp_path / "t.csv"
    make_df(2).to_csv(path, index=False)
    assert SessionFeed.from_csv(path).next()[0] == "SID_0"


def test_store_filter_and_order():
    s = FeedStore()
    s.add(item("a", 0.1, 0, "Low"))
    s.add(item("b", 0.9, 1, "High"))
    assert s.list()[0].id == "b"
    assert len(s.list("Low")) == 1
    assert s.get("a").id == "a" and s.get("zz") is None


def test_agreement_ignores_manual():
    s = FeedStore()
    s.add(item("a", 0.9, 1))
    s.add(item("b", 0.9, 0))
    s.add(item("MAN_00001", 0.9, None))
    assert s.agreement() == (1, 2)


def test_manual_ids_unique_across_threads():
    import threading

    s = FeedStore()
    ids = []
    threads = [threading.Thread(target=lambda: ids.extend(s.next_manual_id() for _ in range(200))) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ids) == len(set(ids)) == 1600
    assert s.next_manual_id() == "MAN_01601"


def test_from_csv_keeps_none_encryption_string(tmp_path):
    path = tmp_path / "t.csv"
    make_df(2).to_csv(path, index=False)  # VALID_SESSION has encryption_used "None"
    assert SessionFeed.from_csv(path).next()[1].encryption_used == "None"
