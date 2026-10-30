#!/usr/bin/env python3
"""Independent checks on the selected ARB resources and optional release bundles."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", action="store_true")
    args = parser.parse_args()
    catalog = ROOT / "packages/im_l10n_catalog/catalog"
    index = load(catalog / "index.json")
    results = []
    for name, relative, locales, count in [
        ("A", "examples/app_a", {"en"}, 20),
        ("SDK for B", "packages/sdk_ui_demo", {"en", "zh"}, 15),
    ]:
        consumer = ROOT / relative
        arbs = sorted((consumer / "lib/l10n/arb").glob("*.arb"))
        data = [load(arb) for arb in arbs]
        require({arb["@@locale"] for arb in data} == locales, f"{name}: locale selection failed")
        for arb in data:
            keys = {key for key in arb if not key.startswith("@")}
            require(len(keys) == count, f"{name}: expected {count} keys")
            require(arb["@chatReadCount"]["placeholders"]["count"]["type"] == "int", "Lost parameter type")
            if name == "A":
                require(arb["authLoginTitle"] == "Sign in to App A", "A override missing")
                require(arb["commonSend"] == "Send", "B override contaminated A")
            else:
                require(not (set(index["modules"]["auth"]) & keys), "B contains auth module")
                require("commonDelete" not in keys, "B contains excluded key")
                require(arb["commonSend"] == ({"en": "Send message", "zh": "发送消息"}[arb["@@locale"]]), "SDK override missing")
        generated = consumer / "lib/l10n/generated"
        require((generated / "app_localizations.dart").is_file(), f"{name}: Dart API missing")
        expected_files = {"app_localizations.dart"} | {f"app_localizations_{locale}.dart" for locale in locales}
        require({path.name for path in generated.glob("*.dart")} == expected_files, f"{name}: stale/unexpected generated locale")
        results.append({"consumer": name, "locales": sorted(locales), "keysPerLocale": count, "translatedValues": count * len(locales)})
    b_packages = load(ROOT / "examples/app_b/.dart_tool/package_config.json")["packages"]
    require("im_l10n_catalog" not in {p["name"] for p in b_packages}, "B pulled the catalog transitively")
    web = []
    if args.web:
        for app in ["a", "b"]:
            folder = ROOT / f"deliverables/app_{app}_web"
            main_js = folder / "main.dart.js"
            require(main_js.is_file(), f"App {app}: release JS missing")
            require(not list(folder.rglob("*.arb")), f"App {app}: raw ARB copied into release")
            require(not any("im_l10n_catalog" in path.parts for path in folder.rglob("*")), "Full catalog copied into release")
            js = main_js.read_text()
            require("Sign in to App A" in js if app == "a" else "Sign in to App A" not in js, "Auth module release boundary failed")
            require("Send message" in js if app == "b" else "Send message" not in js, "Override release boundary failed")
            web.append({"app": app.upper(), "mainJsBytes": main_js.stat().st_size,
                        "mainJsSha256": hashlib.sha256(main_js.read_bytes()).hexdigest(),
                        "rawArbFiles": 0})
    # Production ARBs are now generated. Compare their complete JSON content
    # (including metadata) with the pre-migration semantic baseline, not the
    # obsolete byte hashes of the earlier 20-key demonstration.
    production = ROOT / "evidence/full-integration-flutter-baseline.json"
    verified = 0
    if production.is_file():
        for consumer in load(production)["consumers"].values():
            for raw in consumer["sourceSha256"]:
                path = Path(raw)
                if not path.is_file():
                    continue
                arb = load(path)
                digest = hashlib.sha256(json.dumps(arb, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                require(digest == consumer["semanticSha256"][arb["@@locale"]], f"Production translation changed: {path}")
                verified += 1
    else:
        source = load(ROOT / "evidence/source-inventory.json")
        for raw, digest in source["sourceSha256"].items():
            path = Path(raw)
            if path.is_file():
                require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Original source changed: {path}")
                verified += 1
    report = {"status": "passed", "selection": results, "web": web, "sourceArbSemanticEquivalenceVerified": verified}
    (ROOT / "evidence/bundle-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
