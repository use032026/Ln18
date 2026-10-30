#!/usr/bin/env python3
"""Run each consumer's pinned remote language-resource update/check command."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Use verified cached packages and local Dart dependencies")
    parser.add_argument("--catalog-root", type=Path, help="Explicit unpublished local package override for selected consumers")
    parser.add_argument("--cache-dir", type=Path, help="Optional cache location passed to each consumer")
    parser.add_argument("--only", choices=["mobile", "sdk", "pc"], action="append")
    parser.add_argument("--mobile-root", type=Path, default=Path.home() / "chat-im-cs/lpp/lpp_mobile")
    parser.add_argument("--pc-root", type=Path, default=Path.home() / "chat-im-cs/lpp/lpp_pc_client")
    parser.add_argument("--sdk-root", type=Path, default=Path.home() / "Desktop/IMSDK")
    args = parser.parse_args()
    selected = args.only or ["mobile", "sdk", "pc"]
    entrypoints = {"mobile": "tool/sync_l10n.py", "sdk": "scripts/sync_l10n.py", "pc": "scripts/sync-l10n.py"}
    for name in selected:
        consumer = getattr(args, name + "_root").expanduser().resolve()
        entry = consumer / entrypoints[name]
        if not entry.is_file():
            raise SystemExit(f"Consumer sync command missing: {entry}")
        command = [sys.executable, str(entry)]
        if args.check:
            command.append("--check")
        if args.offline:
            command.append("--offline")
        if args.catalog_root:
            command += ["--catalog-root", str(args.catalog_root.expanduser().resolve())]
        if args.cache_dir:
            command += ["--cache-dir", str(args.cache_dir.expanduser().resolve())]
        subprocess.run(command, check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Language resource sync failed: {error}")
