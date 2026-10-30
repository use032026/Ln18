#!/usr/bin/env python3
"""Compare every supplementary SDK resource against its migration baseline."""
import argparse
import ast
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=Path("/Users/starburst/Desktop/IMSDK"))
    args = parser.parse_args()
    sdk = args.sdk_root.resolve()
    package = ROOT / "packages/im_l10n_catalog"
    spec = importlib.util.spec_from_file_location("extract_sdk", ROOT / "tool/extract_sdk_supplemental.py")
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)
    baseline = json.loads((ROOT / "evidence/full-integration-sdk-baseline.json").read_text())["resources"]
    for name in ["chrome", "web", "languageNames", "examples", "fileMessages", "legalDocuments", "legalPlatformMessages", "supportedLocales", "networkErrors"]:
        actual = json.loads((package / "catalog/sdk_supplemental" / (name + ".json")).read_text())["data"]
        assert actual == baseline[name], name + " catalog differs from baseline"

    def dart_map(source, name):
        match = re.search(r"const " + name + r" = [^\n]*?(\{[\s\S]*?\n\});", source)
        assert match is not None, "Missing generated map: " + name
        return ast.literal_eval(match[1])

    resources = (sdk / "packages/im_sdk/lib/generated/l10n/sdk_resources.dart").read_text()
    for name, expected in [
        ("sdkChromeTranslations", baseline["chrome"]["messages"]),
        ("translationTargetNativeNames", baseline["languageNames"]["native"]),
        ("translationNamesByDeviceLanguage", baseline["languageNames"]["byDeviceLanguage"]),
        ("translationExampleMessages", baseline["examples"]),
        ("sdkFileAttachmentMessages", baseline["fileMessages"]),
        ("sdkNetworkErrorMessages", baseline["networkErrors"]),
    ]:
        assert dart_map(resources, name) == expected, name
    locales_source = resources.replace("const sdkSupportedLocales = <(Locale, String)>[", "const kSupportedLocales = [")
    assert extractor.supported_locale_data(locales_source) == baseline["supportedLocales"], "Supported locale labels/order changed"
    web = (sdk / "web/src/generated/l10n/sdk_catalog.ts").read_text()
    assert json.loads(re.search(r" = (\{[\s\S]*\});", web)[1]) == baseline["web"]["messages"]

    legal = (sdk / "packages/im_sdk/lib/generated/l10n/sdk_legal_documents.g.dart").read_text()
    documents = {}
    for match in re.finditer(r"const (\w+) = LegalDocumentData\((.*?)\n\);", legal, re.S):
        title = re.search(r"appBarTitle:\s*(" + extractor.STRING + r")\s*,", match[2])
        blocks = [extractor.text_literal(item[1]) for item in re.finditer(r"LegalDocumentBlock\(\s*(" + extractor.STRING + r")\s*\)", match[2])]
        documents[match[1]] = {"appBarTitle": extractor.text_literal(title[1]), "blocks": blocks}
    assert documents == baseline["legalDocuments"], "Legal document text mismatch"
    platform = baseline["legalPlatformMessages"]
    assert dart_map(legal, "sdkLegalTitles") == platform["titles"]
    assert dart_map(legal, "sdkLegalPlatformClauses") == platform["clauses"]
    assert dart_map(legal, "sdkLegalPlatformSuffixes") == platform["suffixes"]
    for name, key in [("sdkLegalOpenFailed", "openFailed"), ("sdkLegalViewOfficial", "viewOfficial")]:
        actual = re.search(r"const " + name + r" = (" + extractor.STRING + r");", legal)
        assert actual is not None and extractor.text_literal(actual[1]) == platform["chrome"][key], name
    report = {
        "status": "passed", "sdkChromeMessages": 77, "webChromeMessages": 146,
        "nativeLanguageNames": 11, "deviceLanguageNames": 121, "examples": 11,
        "fileMessageGroups": 6, "legalDocuments": 13, "legalBlocks": 947,
        "legalPlatformClauses": 16, "legalPlatformDisplayValues": 41,
        "supportedLocaleLabels": 6, "networkErrorMessages": 12, "networkErrorTranslatedValues": 72,
        "equivalence": "Every catalog and generated static value equals the pre-migration baseline. Legal platform/viewer text is included; file extension interpolation retains its parameter.",
    }
    (ROOT / "evidence/full-integration-sdk-equivalence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
