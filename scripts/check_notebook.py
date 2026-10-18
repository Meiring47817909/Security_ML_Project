"""Check an executed notebook: no errors, visible outputs, enough figures."""
import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("notebook")
    ap.add_argument("--min-images", type=int, default=0)
    args = ap.parse_args()

    with open(args.notebook, encoding="utf-8") as f:
        nb = json.load(f)

    images = 0
    code_cells = 0
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        code_cells += 1
        outputs = cell.get("outputs", [])
        for out in outputs:
            if out.get("output_type") == "error":
                print(f"FAIL: cell {i} has an error output: {out.get('ename')}: {out.get('evalue')}")
                return 1
            images += "image/png" in out.get("data", {})
        src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        if not outputs and ("plt." in src or "print(" in src):
            print(f"FAIL: cell {i} uses plt./print( but has no outputs")
            return 1
    if images < args.min_images:
        print(f"FAIL: {images} image outputs, expected at least {args.min_images}")
        return 1
    print(f"OK: {code_cells} code cells, no errors, {images} image outputs (min {args.min_images})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
