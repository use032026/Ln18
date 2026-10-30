#!/usr/bin/env python3
"""One-time lossless import of current Flutter ARBs into the public source package."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "packages/im_l10n_catalog"
MOBILE = Path("/Users/starburst/chat-im-cs/lpp/lpp_mobile")
SDK = Path("/Users/starburst/Desktop/IMSDK/packages/im_sdk")
VERSION = "0.2.0"

MODULES = {
    "common": {"common", "nav", "startup", "notice", "toast", "error", "identity"},
    "app": {"app", "privacy", "permission", "legal", "terms"},
    "auth": {"auth"},
    "chat": {"chat", "home", "history", "media", "image", "format", "auto"},
    "settings": {"settings", "network", "timezone", "display", "account", "logged", "font", "about", "diagnostics"},
    "contacts": {"contacts", "friend", "blacklist", "add", "search", "scan"},
    "profile": {"my", "profile"},
    "organization": {"enterprise", "organization", "space", "qr", "group", "join", "invite", "pending", "approval", "request", "recent"},
    "customer_service": {"cs", "customer", "marketing"},
    "calls": {"call"},
    "safety": {"teen", "guardian", "kyc"},
    "official_account": {"official"},
    "feedback": {"feedback"},
    "favorites": {"favorites"},
    "notifications": {"notification"},
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_project(root):
    documents, fingerprints = {}, {}
    yaml = (root / "l10n.yaml").read_text()
    order = [part.strip() for part in re.search(r"preferred-supported-locales:\s*\[([^]]+)\]", yaml).group(1).split(",")]
    for locale in order:
        path = root / f"lib/l10n/app_{locale}.arb"
        raw = path.read_bytes()
        documents[locale] = json.loads(raw)
        fingerprints[str(path)] = sha(raw)
    return documents, fingerprints


def extract():
    mobile, mobile_hash = read_project(MOBILE)
    sdk, sdk_hash = read_project(SDK)
    mobile_keys = [key for key in mobile["zh"] if not key.startswith("@")]
    sdk_keys = [key for key in sdk["zh"] if not key.startswith("@")]
    all_keys = mobile_keys + [key for key in sdk_keys if key not in mobile_keys]
    grouped = {module: [] for module in MODULES}
    for key in all_keys:
        prefix = re.match(r"^[a-z]+", key).group(0)
        matches = [module for module, prefixes in MODULES.items() if prefix in prefixes]
        if len(matches) != 1:
            raise ValueError(f"Unclassified/ambiguous module: {key}")
        grouped[matches[0]].append(key)
    locales = list(mobile) + [locale for locale in sdk if locale not in mobile]
    baseline = {"catalogVersion": VERSION, "scope": "complete Flutter ARBs from current working trees", "consumers": {}}
    for name, documents, keys, hashes in [("chat_mobile", mobile, mobile_keys, mobile_hash), ("im_sdk", sdk, sdk_keys, sdk_hash)]:
        for locale, document in documents.items():
            if {key for key in document if not key.startswith("@")} != set(keys):
                raise ValueError(f"Inconsistent source key set: {name}/{locale}")
        baseline["consumers"][name] = {"locales": list(documents), "keysPerLocale": len(keys), "sourceSha256": hashes,
            "semanticSha256": {locale: sha(json.dumps(document, ensure_ascii=False, sort_keys=True).encode()) for locale, document in documents.items()}}
    save(ROOT / "evidence/full-integration-flutter-baseline.json", baseline)
    for module, keys in grouped.items():
        for locale in locales:
            # Mobile is the shared source; SDK-only keys can still live in a
            # module without inventing translations for unsupported languages.
            arb = {"@@locale": locale}
            for key in keys:
                source = mobile.get(locale, {}) if key in mobile.get(locale, {}) else sdk.get(locale, {})
                if key in source:
                    arb[key] = source[key]
                    if "@" + key in source:
                        arb["@" + key] = source["@" + key]
            save(PACKAGE / f"catalog/{module}/app_{locale}.arb", arb)
    profiles = {}
    for name, documents, keys in [("chat_mobile", mobile, mobile_keys), ("im_sdk", sdk, sdk_keys)]:
        profile = {"schemaVersion": 1, "locales": list(documents), "keys": keys}
        if name == "im_sdk":
            profile["metadata"] = {locale: {key: value for key, value in document.items() if key.startswith("@") and not key.startswith("@@")} for locale, document in documents.items()}
            profile["overrides"] = {locale: {key: document[key] for key in keys if key in mobile.get(locale, {}) and document[key] != mobile[locale][key]} for locale, document in documents.items()}
        save(PACKAGE / f"catalog/profiles/{name}.json", profile)
        profiles[name] = {"locales": len(documents), "keys": len(keys), "overriddenValues": sum(len(v) for v in profile.get("overrides", {}).values())}
    save(PACKAGE / "catalog/index.json", {"schemaVersion": 1, "packageVersion": VERSION, "defaultLocale": "zh", "locales": locales, "modules": grouped})
    pubspec = PACKAGE / "pubspec.yaml"
    pubspec.write_text(re.sub(r"(?m)^version:.*$", f"version: {VERSION}", pubspec.read_text()))
    for root, profile_name, documents in [(MOBILE, "chat_mobile", mobile), (SDK, "im_sdk", sdk)]:
        selected = set(mobile_keys if profile_name == "chat_mobile" else sdk_keys)
        config = {"schemaVersion": 1, "catalogVersion": VERSION, "profile": profile_name,
                  "locales": list(documents), "templateLocale": "zh", "modules": [module for module, keys in grouped.items() if selected.intersection(keys)],
                  "outputDir": "lib/l10n", "outputClass": "AppLocalizations", "layout": "flat"}
        save(root / "l10n.bundle.json", config)
        directory = root / "lib/l10n"
        # Explicit one-time adoption after the entire source has been imported.
        for path in directory.iterdir():
            if path.is_file() and (path.name.startswith("app_") and path.suffix in {".dart", ".arb"}):
                continue
            if path.name == ".im_l10n_catalog_generated":
                continue
            raise ValueError(f"Refusing to adopt unrelated file: {path}")
        (directory / ".im_l10n_catalog_generated").write_text("im_l10n_catalog\n")
        yaml = root / "l10n.yaml"
        header = "# Generated by im_l10n_catalog. Do not edit.\n"
        if not yaml.read_text().startswith(header):
            yaml.write_text(header + yaml.read_text())
    # The original demos retain their original 20/15 keys after the shared
    # modules grow. Their already running Web builds remain untouched.
    for relative in ["examples/app_a", "packages/sdk_ui_demo"]:
        directory = ROOT / relative
        config = json.loads((directory / "l10n.bundle.json").read_text())
        receipt = json.loads((directory / "l10n.bundle.lock.json").read_text())
        config["catalogVersion"] = VERSION
        config["includeKeys"] = receipt["keys"]
        save(directory / "l10n.bundle.json", config)
    print(json.dumps({"profiles": profiles, "modules": {module: len(keys) for module, keys in grouped.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    extract()
