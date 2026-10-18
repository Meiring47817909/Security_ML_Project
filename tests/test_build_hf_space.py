from scripts.build_hf_space import MODEL_FILES, build


def make_project(root):
    for name in ("Dockerfile", "requirements.txt", "README.md"):
        (root / "deploy" / "hf_space").mkdir(parents=True, exist_ok=True)
        (root / "deploy" / "hf_space" / name).write_text(name, encoding="utf-8")
    for pkg in ("intrusion", "model_service"):
        (root / pkg / "__pycache__").mkdir(parents=True)
        (root / pkg / "__init__.py").write_text("", encoding="utf-8")
        (root / pkg / "__pycache__" / "x.pyc").write_bytes(b"0")
    (root / "artifacts").mkdir()
    for name in (*MODEL_FILES, "metrics.csv", "test_sessions.csv"):
        (root / "artifacts" / name).write_text(name, encoding="utf-8")


def test_build_copies_only_what_the_space_needs(tmp_path):
    make_project(tmp_path)
    out = build(tmp_path, tmp_path / "hf_space")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert files == [
        "Dockerfile", "README.md",
        "artifacts/mlp.pt", "artifacts/model_meta.json", "artifacts/preprocess.joblib",
        "intrusion/__init__.py", "model_service/__init__.py", "requirements.txt",
    ]


def test_build_replaces_previous_output(tmp_path):
    make_project(tmp_path)
    out = tmp_path / "hf_space"
    out.mkdir()
    (out / "stale.txt").write_text("old", encoding="utf-8")
    build(tmp_path, out)
    assert not (out / "stale.txt").exists()


def test_build_fails_clearly_without_trained_model(tmp_path):
    make_project(tmp_path)
    (tmp_path / "artifacts" / "mlp.pt").unlink()
    try:
        build(tmp_path, tmp_path / "hf_space")
    except FileNotFoundError as exc:
        assert "mlp.pt" in str(exc) and "notebook" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
