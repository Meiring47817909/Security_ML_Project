"""Assemble the Hugging Face Space folder from the current code and trained model.

Usage (from the project root):  .venv\\Scripts\\python scripts\\build_hf_space.py
Output: hf_space/ (gitignored), ready to upload as a Docker Space. Re-run after retraining the model.
"""
import shutil
import sys
from pathlib import Path

MODEL_FILES = ("mlp.pt", "preprocess.joblib", "model_meta.json")
PACKAGES = ("intrusion", "model_service")
TEMPLATE = Path("deploy") / "hf_space"


def build(project_root: Path, out_dir: Path) -> Path:
    project_root, out_dir = Path(project_root), Path(out_dir)
    artifacts = project_root / "artifacts"
    missing = [name for name in MODEL_FILES if not (artifacts / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"missing model files in {artifacts}: {', '.join(missing)}. Run the notebook first to train and export the model."
        )
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(project_root / TEMPLATE, out_dir)
    for pkg in PACKAGES:
        shutil.copytree(project_root / pkg, out_dir / pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (out_dir / "artifacts").mkdir()
    for name in MODEL_FILES:
        shutil.copy2(artifacts / name, out_dir / "artifacts" / name)
    return out_dir


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    try:
        out = build(root, root / "hf_space")
    except FileNotFoundError as exc:
        sys.exit(str(exc))
    for f in sorted(p for p in out.rglob("*") if p.is_file()):
        print(f"  {f.relative_to(root).as_posix():45s} {f.stat().st_size:>8,d} bytes")
    print(f"Space folder ready: {out}")
