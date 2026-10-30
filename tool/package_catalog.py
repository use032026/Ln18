#!/usr/bin/env python3
"""Create an immutable local version archive without dependency/build caches."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "packages/im_l10n_catalog"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE,
                        help="Source package directory; defaults to packages/im_l10n_catalog")
    parser.add_argument("--check", action="store_true",
                        help="Verify archive file list, contents and CRC without writing; ZIP metadata may differ")
    args = parser.parse_args(argv)
    package = args.package_root.expanduser().resolve()
    version = json.loads((package / "catalog/index.json").read_text())["packageVersion"]
    declared = re.search(r"(?m)^version:\s*(\S+)", (package / "pubspec.yaml").read_text()).group(1)
    if version != declared:
        raise SystemExit("Package/catalog version mismatch")
    files = [package / name for name in ["pubspec.yaml", "pubspec.lock", "README.md", "CHANGELOG.md"]]
    for folder in ["bin", "lib", "catalog", "renderers", "tools", "test"]:
        files.extend(path for path in (package / folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(f"im_l10n_catalog-{version}/" + path.relative_to(package).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    data = stream.getvalue()
    output = ROOT / f"deliverables/im_l10n_catalog-{version}.zip"
    if args.check and not output.is_file():
        raise SystemExit(f"Archive missing: {output}")
    if output.exists():
        existing = output.read_bytes()
        if args.check:
            with zipfile.ZipFile(io.BytesIO(data)) as expected, zipfile.ZipFile(io.BytesIO(existing)) as actual:
                if sorted(actual.namelist()) != sorted(expected.namelist()) or any(
                    actual.read(name) != expected.read(name) for name in expected.namelist()
                ):
                    raise SystemExit("Archive file list or contents differ from the selected source package.")
            data = existing
        elif existing != data:
            raise SystemExit("This version already has a different archive; bump the version rather than replacing it.")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
    report = {"version": version, "file": str(output.relative_to(ROOT)), "bytes": len(data),
              "files": len(files), "sha256": hashlib.sha256(data).hexdigest(), "remotePublished": False}
    if args.check:
        report["mode"] = "check"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(data)
    (ROOT / f"evidence/catalog-archive-{version}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
