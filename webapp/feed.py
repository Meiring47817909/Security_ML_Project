"""Replay feed of test sessions and the in-memory store of scored sessions."""
import threading
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from intrusion.preprocess import ORIGINAL_FEATURES, Session


@dataclass
class ScoredSession:
    id: str
    session: Session
    true_label: int | None
    probability: float
    risk: str
    source: str
    created: datetime
    pattern: str
    actions: list[str]


class SessionFeed:
    def __init__(self, df: pd.DataFrame):
        self._df = df.reset_index(drop=True)
        self._pos = 0
        self._lock = threading.Lock()

    @classmethod
    def from_csv(cls, path) -> "SessionFeed":
        return cls(pd.read_csv(path, keep_default_na=False))

    def next(self) -> tuple[str, Session, int]:
        with self._lock:
            row = self._df.iloc[self._pos]
            self._pos = (self._pos + 1) % len(self._df)
        session = Session(**{k: row[k].item() if hasattr(row[k], "item") else row[k] for k in ORIGINAL_FEATURES})
        return str(row["session_id"]), session, int(row["attack_detected"])


class FeedStore:
    def __init__(self):
        self._items: list[ScoredSession] = []
        self._manual = 0
        self._lock = threading.Lock()

    def next_manual_id(self) -> str:
        with self._lock:
            self._manual += 1
            return f"MAN_{self._manual:05d}"

    def add(self, item: ScoredSession) -> None:
        with self._lock:
            self._items.append(item)

    def get(self, id: str) -> ScoredSession | None:
        return next((i for i in self._items if i.id == id), None)

    def list(self, risk: str | None = None) -> list[ScoredSession]:
        items = reversed(self._items)
        return [i for i in items if risk is None or i.risk == risk]

    def agreement(self) -> tuple[int, int]:
        labelled = [i for i in self._items if i.true_label is not None]
        matches = sum(int(i.probability >= 0.5) == i.true_label for i in labelled)
        return matches, len(labelled)
