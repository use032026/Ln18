#!/usr/bin/env python3
"""Copy a small, reproducible ARB sample; source projects are always read-only."""
import argparse
import hashlib
import json
from pathlib import Path


LOCALES = ["zh", "zh_TW", "en", "ja", "ko", "vi"]
MODULES = {
    "common": ["commonConfirm", "commonCancel", "commonSave", "commonDelete", "commonSend", "commonRetry"],
    "auth": ["authLoginTitle", "authLoginButton", "authHintEmail", "authHintPassword"],
    "chat": ["chatInputHint", "chatReadCount", "chatRecalledPeer", "chatReplyTo", "chatGroupMemberCount", "chatHomeNewMessages", "formatMinutesAgo"],
    "settings": ["settingsTitle", "settingsLanguage", "settingsSignOutDeviceConfirm"],
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_source(root):
    documents, fingerprints = {}, {}
    for locale in LOCALES:
        path = root / f"app_{locale}.arb"
        raw = path.read_bytes()
        documents[locale] = json.loads(raw)
        fingerprints[str(path)] = hashlib.sha256(raw).hexdigest()
    return documents, fingerprints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile-l10n", type=Path, required=True)
    parser.add_argument("--sdk-l10n", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    index = root / "packages/im_l10n_catalog/catalog/index.json"
    if index.exists() and json.loads(index.read_text())["packageVersion"] != "0.1.0":
        raise SystemExit("The 0.1.0 sample importer is historical. Use extract_full.py for the production catalog.")
    mobile, source_hashes = read_source(args.mobile_l10n.resolve())
    sdk, sdk_hashes = read_source(args.sdk_l10n.resolve())
    template = mobile["zh"]
    all_keys = [key for keys in MODULES.values() for key in keys]
    # Finish all source checks before writing the new sample.
    for locale in LOCALES:
        for key in all_keys:
            if not isinstance(mobile[locale].get(key), str):
                raise ValueError(f"Missing translation: {locale}/{key}")
            if "@" + key not in template:
                raise ValueError(f"Missing template metadata: {key}")
    catalog = root / "packages/im_l10n_catalog/catalog"
    index = {"schemaVersion": 1, "packageVersion": "0.1.0", "defaultLocale": "zh", "locales": LOCALES, "modules": MODULES}
    save(catalog / "index.json", index)
    for module, keys in MODULES.items():
        for locale in LOCALES:
            arb = {"@@locale": locale}
            for key in keys:
                arb[key] = mobile[locale][key]
                # The real projects keep parameter types primarily in the zh template.
                arb["@" + key] = template["@" + key]
            save(catalog / module / f"app_{locale}.arb", arb)
    app_keys = {key for key in template if not key.startswith("@")}
    sdk_keys = {key for key in sdk["zh"] if not key.startswith("@")}
    shared = app_keys & sdk_keys
    differences = {}
    for locale in LOCALES:
        differences[locale] = [
            key for key in sorted(shared) if mobile[locale][key] != sdk[locale][key]
        ]
    report = {
        "capturedOn": "2026-10-29",
        "scope": "20 real chat-im-cs keys, six locales; example extraction, not a full migration",
        "sourceOfTruth": "chat-im-cs ARB values; zh ARB metadata",
        "mobileKeysPerLocale": {locale: sum(not key.startswith("@") for key in data) for locale, data in mobile.items()},
        "sdkKeysPerLocale": {locale: sum(not key.startswith("@") for key in data) for locale, data in sdk.items()},
        "sharedKeys": len(shared), "mobileOnlyKeys": len(app_keys - sdk_keys), "sdkOnlyKeys": len(sdk_keys - app_keys),
        "selectedKeys": all_keys, "differences": differences,
        "sourceSha256": source_hashes | sdk_hashes,
    }
    save(root / "evidence/source-inventory.json", report)
    print(f"Extracted {len(all_keys)} keys × {len(LOCALES)} locales into {catalog}")
    print("Both source projects were opened read-only. SDK/App differences recorded for later ownership decisions.")


if __name__ == "__main__":
    main()
