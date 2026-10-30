#!/usr/bin/env python3
"""Export version-pinned resources without adding runtime/path dependencies."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def target(root, relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in {".", ".."} for p in path.parts):
        raise ValueError(f"Unsafe generated path: {relative}")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink output: {current}")
    if not current.resolve().is_relative_to(root):
        raise ValueError(f"Output outside consumer: {relative}")
    return current


def write_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".l10n-", delete=False) as file:
        file.write(content)
        temporary = file.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--config", default="l10n.resources.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dart", default="dart")
    args = parser.parse_args()
    root = args.consumer_root.resolve(strict=True)
    config = read(target(root, args.config))
    version = read(PACKAGE / "catalog/index.json")["packageVersion"]
    pub_version = next(line.partition(":")[2].strip() for line in (PACKAGE / "pubspec.yaml").read_text().splitlines() if line.startswith("version:"))
    if config.get("schemaVersion") != 1 or config.get("catalogVersion") != version or pub_version != version:
        raise ValueError("Resource schema/version mismatch. Update the consumer and package together.")
    renderer = config.get("renderer")
    if renderer not in {"mobile", "sdk", "pc"}:
        raise ValueError(f"Unknown resource renderer: {renderer}")
    script = PACKAGE / f"renderers/{renderer}.py"
    spec = importlib.util.spec_from_file_location(f"im_l10n_{renderer}", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rendered = module.render(PACKAGE, root, config)
    if not isinstance(rendered, dict) or not rendered:
        raise ValueError("Resource renderer produced no output.")
    outputs = {relative: text.encode("utf-8") for relative, text in rendered.items()}
    paths = {relative: target(root, relative) for relative in outputs}
    receipt_path = target(root, "l10n.resources.lock.json")
    previous = read(receipt_path) if receipt_path.exists() else None
    if previous is not None and previous.get("generatedBy") != "im_l10n_catalog":
        raise ValueError("Existing resource receipt is not owned by im_l10n_catalog.")
    # Never silently abandon or delete an older generated resource path.
    if previous and set(previous["outputs"]) - set(outputs):
        raise ValueError("Generated output paths changed; migrate old paths explicitly.")
    flutter = config.get("flutterBundle")
    if flutter:
        bundle_config = target(root, flutter)
        packages = PACKAGE / ".dart_tool/package_config.json"
        if not packages.is_file():
            if args.check:
                raise ValueError("Check mode is read-only. Run dart pub get in the catalog package first.")
            subprocess.run([args.dart, "pub", "get"], cwd=PACKAGE, check=True)
        command = [args.dart, f"--packages={packages}", str(PACKAGE / "bin/generate.dart"), bundle_config.name]
        if args.check:
            command.append("--check")
        subprocess.run(command, cwd=bundle_config.parent, check=True)
    dataset = PACKAGE / "catalog" / ("pc" if renderer == "pc" else f"{renderer}_supplemental")
    sources = [script] + sorted(path for path in dataset.rglob("*") if path.is_file())
    receipt = {"generatedBy": "im_l10n_catalog", "schemaVersion": 1, "catalogVersion": version,
               "renderer": renderer, "sourceSha256": {str(path.relative_to(PACKAGE)): digest(path.read_bytes()) for path in sources},
               "outputs": {relative: digest(data) for relative, data in sorted(outputs.items())}}
    if flutter:
        receipt["flutterBundleSha256"] = read(bundle_config.parent / "l10n.bundle.lock.json")["bundleSha256"]
    if args.check:
        stale = [relative for relative, data in outputs.items() if not paths[relative].is_file() or paths[relative].read_bytes() != data]
        if stale or previous != receipt:
            raise ValueError(f"Generated resources are stale: {', '.join(stale) or 'receipt'}. Run sync_l10n.")
        print(f"Verified {renderer}: {len(outputs)} resource files, catalog {version}.")
        return
    for relative, data in outputs.items():
        if not paths[relative].is_file() or paths[relative].read_bytes() != data:
            write_atomic(paths[relative], data)
    write_atomic(receipt_path, (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"Generated {renderer}: {len(outputs)} resource files, catalog {version}.")
    if flutter:
        print(f"Next: run flutter gen-l10n in {bundle_config.parent}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Translation resource sync failed: {error}")
