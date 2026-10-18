"""Raw data access, quality checks, cleaning and splitting. The raw CSV is read-only."""
import hashlib
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

DATASET = "dnkumars/cybersecurity-intrusion-detection-dataset"
RAW_FILENAME = "cybersecurity_intrusion_data.csv"
TARGET = "attack_detected"
ID_COLUMN = "session_id"


def raw_path() -> Path:
    import kagglehub

    return Path(kagglehub.dataset_download(DATASET)) / RAW_FILENAME


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or raw_path())


def quality_report(df: pd.DataFrame) -> dict:
    missing = df.isna().sum()
    numeric = df.select_dtypes("number")
    return {
        "rows": len(df),
        "missing": {c: int(n) for c, n in missing.items() if n > 0},
        "duplicates": int(df.duplicated().sum()),
        "failed_gt_attempts": int((df["failed_logins"] > df["login_attempts"]).sum()),
        "ranges": {c: (float(numeric[c].min()), float(numeric[c].max())) for c in numeric.columns},
    }


def fill_missing_encryption(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["encryption_used"] = out["encryption_used"].fillna("None")
    return out


def drop_identifier(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[ID_COLUMN], errors="ignore")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    return drop_identifier(fill_missing_encryption(df))


def split(df: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, rest = train_test_split(df, test_size=0.30, stratify=df[TARGET], random_state=seed)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest[TARGET], random_state=seed)
    return train, val, test
