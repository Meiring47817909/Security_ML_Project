"""Feature preprocessing and the validated Session input schema."""
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = [
    "network_packet_size",
    "login_attempts",
    "session_duration",
    "ip_reputation_score",
    "failed_logins",
    "unusual_time_access",
]
CATEGORICAL = ["protocol_type", "encryption_used", "browser_type"]
CATEGORIES = {
    "protocol_type": ["ICMP", "TCP", "UDP"],
    "encryption_used": ["AES", "DES", "None"],
    "browser_type": ["Chrome", "Edge", "Firefox", "Safari", "Unknown"],
}
ORIGINAL_FEATURES = NUMERIC + CATEGORICAL


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC),
            (
                "cat",
                OneHotEncoder(
                    categories=[CATEGORIES[c] for c in CATEGORICAL],
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                CATEGORICAL,
            ),
        ]
    )


def feature_names(pre: ColumnTransformer) -> list[str]:
    return list(pre.get_feature_names_out())


def original_feature(encoded_name: str) -> str:
    """Map an encoded feature name back to its original column."""
    name = encoded_name.split("__", 1)[1] if "__" in encoded_name else encoded_name
    for col in CATEGORICAL:
        if name.startswith(col + "_"):
            return col
    return name


class Session(BaseModel):
    network_packet_size: int = Field(ge=1, le=65535)
    protocol_type: Literal["ICMP", "TCP", "UDP"]
    login_attempts: int = Field(ge=0, le=100)
    session_duration: float = Field(ge=0, allow_inf_nan=False)
    encryption_used: Literal["AES", "DES", "None"]
    ip_reputation_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    failed_logins: int = Field(ge=0, le=100)
    browser_type: Literal["Chrome", "Edge", "Firefox", "Safari", "Unknown"]
    unusual_time_access: int = Field(ge=0, le=1)


def to_frame(sessions: list[Session]) -> pd.DataFrame:
    return pd.DataFrame([s.model_dump() for s in sessions])[ORIGINAL_FEATURES]
