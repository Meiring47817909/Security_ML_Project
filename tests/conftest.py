import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def raw_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 200
    login_attempts = rng.integers(1, 10, n)
    failed = np.minimum(rng.integers(0, 6, n), login_attempts)
    failed[:5] = login_attempts[:5] + 1  # a few rows with failed_logins > login_attempts
    enc = rng.choice(["AES", "DES"], n).astype(object)
    enc[rng.random(n) < 0.2] = np.nan
    attack = np.zeros(n, dtype=int)
    attack[rng.permutation(n)[:90]] = 1  # 45% positives
    return pd.DataFrame(
        {
            "session_id": [f"SID_{i:05d}" for i in range(1, n + 1)],
            "network_packet_size": rng.integers(64, 1500, n),
            "protocol_type": rng.choice(["ICMP", "TCP", "UDP"], n),
            "login_attempts": login_attempts,
            "session_duration": rng.exponential(800.0, n),
            "encryption_used": enc,
            "ip_reputation_score": rng.random(n),
            "failed_logins": failed,
            "browser_type": rng.choice(["Chrome", "Edge", "Firefox", "Safari", "Unknown"], n),
            "unusual_time_access": rng.integers(0, 2, n),
            "attack_detected": attack,
        }
    )


@pytest.fixture
def raw_csv(tmp_path, raw_df):
    path = tmp_path / "raw.csv"
    raw_df.to_csv(path, index=False)
    return path


VALID_SESSION = {
    "network_packet_size": 500,
    "protocol_type": "TCP",
    "login_attempts": 4,
    "session_duration": 300.0,
    "encryption_used": "None",
    "ip_reputation_score": 0.3,
    "failed_logins": 1,
    "browser_type": "Chrome",
    "unusual_time_access": 0,
}


@pytest.fixture
def artifacts_dir(tmp_path, raw_df):
    import torch

    from intrusion.data import clean, split
    from intrusion.inference import save_artifacts
    from intrusion.model import MLP
    from intrusion.preprocess import ORIGINAL_FEATURES, build_preprocessor

    train = split(clean(raw_df))[0]
    pre = build_preprocessor().fit(train[ORIGINAL_FEATURES])
    torch.manual_seed(42)
    model = MLP()
    out = tmp_path / "artifacts"
    save_artifacts(out, model, pre, version="test")
    return out
