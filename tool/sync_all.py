#!/usr/bin/env python3
"""Sync/check the three production consumers using their existing toolchains."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "packages/im_l10n_catalog"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--only", choices=["mobile", "sdk", "pc"], action="append")
    parser.add_argument("--mobile-root", type=Path, default=Path.home() / "chat-im-cs/lpp/lpp_mobile")
    parser.add_argument("--pc-root", type=Path, default=Path.home() / "chat-im-cs/lpp/lpp_pc_client")
    parser.add_argument("--sdk-root", type=Path, default=Path.home() / "Desktop/IMSDK")
    args = parser.parse_args()
    selected = args.only or ["mobile", "sdk", "pc"]
    for name in selected:
        consumer = getattr(args, name + "_root").expanduser().resolve()
        command = [sys.executable, str(PACKAGE / "tools/sync.py"), "--consumer-root", str(consumer)]
        flutter = None
        if name == "mobile":
            flutter = consumer / ".fvm/flutter_sdk/bin/flutter"
        elif name == "sdk":
            version = (consumer / ".flutter-version").read_text().strip()
            flutter = Path.home() / f"fvm/versions/{version}/bin/flutter"
        if flutter:
            if not flutter.is_file():
                raise SystemExit(f"Project Flutter toolchain missing: {flutter}")
            command += ["--dart", str(flutter.parent / "dart")]
        if args.check:
            command.append("--check")
        subprocess.run(command, check=True)
        if flutter and not args.check:
            workdir = consumer if name == "mobile" else consumer / "packages/im_sdk"
            subprocess.run([str(flutter), "gen-l10n"], cwd=workdir, check=True)


if __name__ == "__main__":
    main()
