#!/usr/bin/env python3
"""Verify generated PC dictionaries are semantically identical to extraction."""
import argparse
import hashlib
import json
import runpy
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    helpers = runpy.run_path(str(root / "tool/extract_pc.py"))
    baseline = json.loads((root / "evidence/full-integration-pc-baseline.json").read_text())
    result = subprocess.run(["node", "--input-type=module", "-"], input=helpers["NODE_EXTRACT"], cwd=args.pc_root,
                            text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout)
    records = {}
    for locale, dictionary in actual["locales"].items():
        prior = baseline["locales"][locale]
        leaves = helpers["flatten"](dictionary)
        assert helpers["canonical_hash"](leaves) == prior["leafSha256"], f"Leaf values changed: {locale}"
        assert helpers["canonical_hash"](dictionary) == prior["objectSha256"], f"Object/array values changed: {locale}"
        assert hashlib.sha256(json.dumps(dictionary, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() == prior["orderedObjectSha256"], f"Object property order changed: {locale}"
        assert helpers["shape"](dictionary) == prior["shape"], f"Object/array shape changed: {locale}"
        records[locale] = {"keys": len(leaves), "leafSha256": prior["leafSha256"], "objectAndArrayShapePreserved": True}
    assert helpers["canonical_hash"](actual["fallbacks"]) == baseline["fallbacksSha256"], "Fallback exports changed"
    report = {"status": "passed", "locales": records, "fallbackExportsPreserved": True}
    (root / "evidence/full-integration-pc-equivalence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
