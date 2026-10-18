import numpy as np
import pydantic
import pytest

from conftest import VALID_SESSION as VALID
from intrusion.data import TARGET, clean, split
from intrusion.preprocess import (
    ORIGINAL_FEATURES,
    Session,
    build_preprocessor,
    feature_names,
    original_feature,
    to_frame,
)


def test_preprocessor_outputs_17_scaled_features(raw_df):
    tr, _, _ = split(clean(raw_df))
    pre = build_preprocessor().fit(tr.drop(columns=TARGET))
    X = pre.transform(tr.drop(columns=TARGET))
    assert X.shape == (140, 17) and len(feature_names(pre)) == 17
    assert np.allclose(X[:, :6].mean(axis=0), 0, atol=1e-6)


def test_original_feature_mapping():
    assert original_feature("cat__browser_type_Unknown") == "browser_type"
    assert original_feature("num__failed_logins") == "failed_logins"


def test_session_accepts_none_encryption():
    s = Session(**VALID)
    assert s.encryption_used == "None"


@pytest.mark.parametrize(
    "field,value",
    [
        ("ip_reputation_score", 1.5),
        ("login_attempts", -1),
        ("browser_type", "Opera"),
        ("unusual_time_access", 2),
        ("network_packet_size", 0),
        ("session_duration", -0.1),
        ("session_duration", float("inf")),
    ],
)
def test_session_rejects_out_of_range(field, value):
    with pytest.raises(pydantic.ValidationError):
        Session(**{**VALID, field: value})


def test_session_allows_failed_greater_than_attempts():
    Session(**{**VALID, "login_attempts": 1, "failed_logins": 3})


def test_to_frame_column_order():
    assert list(to_frame([Session(**VALID)]).columns) == ORIGINAL_FEATURES
