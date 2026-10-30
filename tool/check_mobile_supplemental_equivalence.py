#!/usr/bin/env python3
"""Check every extracted mobile supplemental value against its saved baseline."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mobile_extract", ROOT / "tool/extract_mobile_supplemental.py")
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def literal_constants(source):
    return {match[1]: extract.text_literal(match[2])
            for match in re.finditer(r"const (\w+)\s*=\s*(" + extract.STRING + r")\s*;", source)}


def token_digest(source):
    """Ignore formatting outside string literals, preserving predicate contents."""
    pieces, end = [], 0
    for match in re.finditer(extract.STRING, source):
        pieces += [re.sub(r"\s+", "", source[end:match.start()]), match[0]]
        end = match.end()
    pieces.append(re.sub(r"\s+", "", source[end:]))
    return hashlib.sha256("".join(pieces).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile-root", required=True, type=Path)
    args = parser.parse_args()
    mobile = args.mobile_root.resolve()
    baseline = json.loads((ROOT / "evidence/full-integration-mobile-baseline.json").read_text())
    extra = baseline["extendedResources"]
    names = (mobile / "lib/generated/l10n/translation_language_names.dart").read_text()
    assert extract.digest(extract.canonical(extract.dart_map(names, "translationTargetNativeNames"))) == baseline["nativeNamesSha256"]
    assert extract.digest(extract.canonical(extract.dart_map(names, "translationTargetNamesByDeviceLanguage"))) == baseline["localizedNamesSha256"]
    legal_part = (mobile / "lib/generated/l10n/mobile_legal_documents.g.dart").read_text()
    documents = {}
    for match in re.finditer(r"const (\w+) = LegalDocumentData\((.*?)\n\);", legal_part, re.S):
        title = re.search(r"appBarTitle:\s*(" + extract.STRING + r")\s*,", match[2])
        documents[match[1]] = {"appBarTitle": extract.text_literal(title[1]),
                              "blocks": [extract.text_literal(row[1]) for row in re.finditer(r"LegalDocumentBlock\(\s*(" + extract.STRING + r")\s*\)", match[2])]}
    assert documents == extra["legalDocuments"]["documents"], "Legal document text changed"
    assert literal_constants(legal_part) == extra["legalDocuments"]["platformTexts"], "Platform legal text changed"
    legal_source = (mobile / "lib/features/settings/presentation/pages/legal_document_page.dart").read_text()
    logic = legal_source[legal_source.index("LegalDocumentData termsLegalDocumentForPlatform"):legal_source.index("class LegalDocumentScaffold")]
    assert token_digest(logic) == baseline["legalPlatformTokenSha256"], "Platform predicate/fallback logic changed"
    examples = (mobile / "lib/generated/l10n/mobile_translation_examples.dart").read_text()
    constants = literal_constants(examples)
    expected = extra["translationExamples"]
    assert constants["mobileTranslationOriginalExample"] == expected["source"]
    assert constants["mobileTranslationExampleFallback"] == expected["fallback"]
    assert extract.dart_map(examples, "mobileTranslationExampleMessages") == expected["translations"]
    locale_source = (mobile / "lib/generated/l10n/mobile_supported_locales.dart").read_text()
    locales = []
    for match in re.finditer(r"\(Locale\((" + extract.STRING + r")(?:,\s*(" + extract.STRING + r"))?\),\s*(" + extract.STRING + r")\)", locale_source):
        locales.append({"languageCode": extract.text_literal(match[1]), "countryCode": extract.text_literal(match[2]) if match[2] else None,
                        "nativeName": extract.text_literal(match[3])})
    assert locales == extra["supportedLocales"], "Supported locale order or native name changed"
    native_count = 0
    for relative, before in baseline["sourceSha256"].items():
        if relative.startswith(("ios/Runner/", "android/")) and relative.endswith((".strings", ".xml")):
            assert hashlib.sha256((mobile / relative).read_bytes()).hexdigest() == before, relative
            native_count += 1
    result = {"status": "passed", "targetNativeNames": baseline["targetLanguageCount"],
              "localizedTargetNames": baseline["localizedNameCount"], "supportedLocaleNames": len(locales),
              "translationExamples": len(expected["translations"]), "originalExample": True, "originalFallback": True,
              "legalDocuments": len(documents), "legalBlocks": sum(len(row["blocks"]) for row in documents.values()),
              "platformLegalTexts": len(extra["legalDocuments"]["platformTexts"]), "platformLogicPreserved": True,
              "nativeFilesByteIdentical": native_count}
    (ROOT / "evidence/full-integration-mobile-supplemental-equivalence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
