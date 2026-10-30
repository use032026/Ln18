#!/usr/bin/env python3
"""Generate the A/B example; optionally verify it and build release Web bundles."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Run analysis and focused tests")
    parser.add_argument("--build-web", action="store_true", help="Keep release Web bundles under deliverables/")
    args = parser.parse_args()
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    commands = []

    def run(label, relative, command):
        print(f"{label} …", flush=True)
        started = time.monotonic()
        log = evidence / f"{label}.log"
        with log.open("w") as output:
            output.write(f"cwd: {relative}\ncommand: {json.dumps(command)}\n\n")
            output.flush()
            result = subprocess.run(command, cwd=ROOT / relative, stdout=output, stderr=subprocess.STDOUT)
        commands.append({"step": label, "cwd": relative, "command": command, "exitCode": result.returncode,
                         "seconds": round(time.monotonic() - started, 2), "log": str(log.relative_to(ROOT))})
        (evidence / "commands.json").write_text(json.dumps(commands, ensure_ascii=False, indent=2) + "\n")
        if result.returncode:
            print(log.read_text(), file=sys.stderr)
            raise SystemExit(f"{label} failed. Inspect {log}")
        print(f"{label}: OK", flush=True)

    run("catalog-pub-get", "packages/im_l10n_catalog", ["dart", "pub", "get"])
    # The generated files are retained in the example. On first use the local
    # generator can also be invoked before Flutter pub get, without a Flutter app.
    for name, relative in [("a", "examples/app_a"), ("sdk", "packages/sdk_ui_demo")]:
        run(f"{name}-pub-get", relative, ["flutter", "pub", "get"])
        run(f"{name}-select", relative, ["dart", "run", "im_l10n_catalog:generate", "l10n.bundle.json"])
        run(f"{name}-gen-l10n", relative, ["flutter", "gen-l10n"])
    run("b-pub-get", "examples/app_b", ["flutter", "pub", "get"])

    if args.verify:
        run("catalog-analyze", "packages/im_l10n_catalog", ["dart", "analyze"])
        run("catalog-tests", "packages/im_l10n_catalog", ["dart", "test", "--reporter=expanded"])
        for name, relative in [("a", "examples/app_a"), ("sdk", "packages/sdk_ui_demo"), ("b", "examples/app_b")]:
            run(f"{name}-analyze", relative, ["flutter", "analyze", "--no-pub"])
            run(f"{name}-tests", relative, ["flutter", "test", "--no-pub", "--reporter=expanded"])

    if args.build_web:
        for name in ["a", "b"]:
            run(f"{name}-web-release", f"examples/app_{name}", [
                "flutter", "build", "web", "--release", "--no-pub", "--no-wasm-dry-run",
                "--no-web-resources-cdn", "--pwa-strategy=none", "--output", str(ROOT / f"deliverables/app_{name}_web"),
            ])
    audit_command = [sys.executable, "tool/audit_demo.py"]
    if args.build_web:
        audit_command.append("--web")
    run("bundle-audit", ".", audit_command)
    print("Done. Configurations, generated resources and logs are retained in Ln18.", flush=True)


if __name__ == "__main__":
    main()
