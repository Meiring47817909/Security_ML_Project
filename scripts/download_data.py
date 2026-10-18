"""Fetch the dataset into the kagglehub cache and print its location, size and hash."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intrusion.data import file_sha256, load_raw, raw_path  # noqa: E402

if __name__ == "__main__":
    path = raw_path()
    print(f"path: {path}")
    print(f"rows: {len(load_raw(path))}")
    print(f"sha256: {file_sha256(path)}")
