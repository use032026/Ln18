#!/usr/bin/env python3
"""Create an immutable local version archive without dependency/build caches."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "packages/im_l10n_catalog"


def main():
    version = json.loads((PACKAGE / "catalog/index.json").read_text())["packageVersion"]
    declared = re.search(r"(?m)^version:\s*(\S+)", (PACKAGE / "pubspec.yaml").read_text()).group(1)
    if version != declared:
        raise SystemExit("Package/catalog version mismatch")
    files = [PACKAGE / name for name in ["pubspec.yaml", "pubspec.lock", "README.md", "CHANGELOG.md"]]
    for folder in ["bin", "lib", "catalog", "renderers", "tools", "test"]:
        files.extend(path for path in (PACKAGE / folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(f"im_l10n_catalog-{version}/" + path.relative_to(PACKAGE).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    data = stream.getvalue()
    output = ROOT / f"deliverables/im_l10n_catalog-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    if output.exists() and output.read_bytes() != data:
        raise SystemExit("This version already has a different archive; bump the version rather than replacing it.")
    output.write_bytes(data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    report = {"version": version, "file": str(output.relative_to(ROOT)), "bytes": len(data),
              "files": len(files), "sha256": hashlib.sha256(data).hexdigest(), "remotePublished": False}
    (ROOT / f"evidence/catalog-archive-{version}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
