import pandas as pd

from intrusion.data import (
    clean,
    drop_identifier,
    file_sha256,
    fill_missing_encryption,
    load_raw,
    quality_report,
    split,
)


def test_fill_missing_encryption_does_not_mutate(raw_df):
    before = raw_df.copy(deep=True)
    out = fill_missing_encryption(raw_df)
    pd.testing.assert_frame_equal(raw_df, before)
    assert out["encryption_used"].isna().sum() == 0
    assert (out["encryption_used"] == "None").sum() == before["encryption_used"].isna().sum()


def test_drop_identifier_does_not_mutate(raw_df):
    before = raw_df.copy(deep=True)
    out = drop_identifier(raw_df)
    pd.testing.assert_frame_equal(raw_df, before)
    assert "session_id" not in out.columns and "session_id" in raw_df.columns


def test_quality_report(raw_df):
    r = quality_report(raw_df)
    assert r["rows"] == 200
    assert r["missing"] == {"encryption_used": int(raw_df["encryption_used"].isna().sum())}
    assert r["failed_gt_attempts"] == int((raw_df.failed_logins > raw_df.login_attempts).sum())


def test_split_sizes_and_stratification(raw_df):
    tr, va, te = split(clean(raw_df))
    assert (len(tr), len(va), len(te)) == (140, 30, 30)
    rate = raw_df["attack_detected"].mean()
    for part in (tr, va, te):
        assert abs(part["attack_detected"].mean() - rate) < 0.05
    assert set(tr.index).isdisjoint(va.index) and set(tr.index).isdisjoint(te.index)


def test_split_is_deterministic(raw_df):
    a = split(clean(raw_df))
    b = split(clean(raw_df))
    assert all(x.index.equals(y.index) for x, y in zip(a, b))


def test_loading_and_cleaning_never_change_raw_file(raw_csv):
    h = file_sha256(raw_csv)
    clean(load_raw(raw_csv))
    assert file_sha256(raw_csv) == h
