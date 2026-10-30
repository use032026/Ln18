#!/usr/bin/env python3
"""One-time extraction of mobile language-name and native resources.

Normal consumer regeneration reads the extracted catalog, not either original
repository. This script can also re-read the generated language-name constants
after the first migration, so the extraction remains reproducible.
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

STRING = r"r?'''[\s\S]*?'''|r?\"\"\"[\s\S]*?\"\"\"|r?'(?:\\.|[^'\\])*'|r?\"(?:\\.|[^\"\\])*\""


def text_literal(token):
    if token.startswith("r"):
        delimiter = token[1:4] if token[1:4] in ("'''", '\"\"\"') else token[1]
        return token[1 + len(delimiter):-len(delimiter)]
    return ast.literal_eval(token)


def legal_resources(source):
    """Return original legal text and display-only replacement spans.

    The predicate strings in _platformizeLegalText are intentionally excluded:
    they match the existing legal paragraphs and are application logic.
    """
    documents, changes = {}, []
    for match in re.finditer(r"const (\w+) = LegalDocumentData\((.*?)\n\);", source, re.S):
        title = re.search(r"appBarTitle:\s*(" + STRING + r")\s*,", match[2])
        blocks = [text_literal(item[1]) for item in re.finditer(r"LegalDocumentBlock\(\s*(" + STRING + r")\s*\)", match[2])]
        if title is None or not blocks:
            raise ValueError("Unable to parse mobile legal document: " + match[1])
        documents[match[1]] = {"appBarTitle": text_literal(title[1]), "blocks": blocks}
        changes.append((match.start(), match.end(), ""))
    if len(documents) != 13:
        raise ValueError("Expected 13 mobile legal documents; use --baseline after migration")
    platform_texts = {}
    title_start = source.index("LegalDocumentData termsLegalDocumentForPlatform")
    title_end = source.index("LegalDocumentData _platformDocument", title_start)
    for index, match in enumerate(re.finditer(STRING, source[title_start:title_end]), 1):
        symbol = f"_mobileLegalHeading{index:03}"
        platform_texts[symbol] = text_literal(match[0])
        changes.append((title_start + match.start(), title_start + match.end(), symbol))
    platform_start = source.index("String? _platformizeLegalText")
    platform_end = source.index("\nconst termsLegalDocumentZhTw", platform_start)
    platform = source[platform_start:platform_end]
    pattern = r"return\s+isIos\s*\?\s*(" + STRING + r"|null)\s*:\s*(" + STRING + r"|null)\s*;"
    returns = list(re.finditer(pattern, platform))
    if len(returns) != 16 or len(platform_texts) != 6:
        raise ValueError("Mobile platform-specific legal structure changed")
    for index, match in enumerate(returns, 1):
        for group, suffix in [(1, "Ios"), (2, "Android")]:
            token = match[group]
            if token == "null":
                continue
            symbol = f"_mobileLegalParagraph{index:03}{suffix}"
            platform_texts[symbol] = text_literal(token)
            changes.append((platform_start + match.start(group), platform_start + match.end(group), symbol))
    replacements = list(re.finditer(r"text\.replaceFirst\(\s*(?:" + STRING + r"),\s*(" + STRING + r")\s*\)", platform))
    if len(replacements) != 2:
        raise ValueError("Expected two platform label replacements")
    for index, match in enumerate(replacements, 1):
        symbol = f"_mobileLegalPlatformSuffix{index:03}"
        platform_texts[symbol] = text_literal(match[1])
        changes.append((platform_start + match.start(1), platform_start + match.end(1), symbol))
    normalized = source
    for start, end, replacement in sorted(changes, reverse=True):
        normalized = normalized[:start] + replacement + normalized[end:]
    logic_start = normalized.index("LegalDocumentData termsLegalDocumentForPlatform")
    logic_end = normalized.index("class LegalDocumentScaffold", logic_start)
    logic = normalized[logic_start:logic_end].rstrip()
    return {"documents": documents, "platformTexts": platform_texts}, changes, digest(logic.encode())


def additional_resources(mobile):
    legal = mobile / "lib/features/settings/presentation/pages/legal_document_page.dart"
    examples = mobile / "lib/features/settings/presentation/pages/auto_translate_page.dart"
    locales = mobile / "lib/core/providers/locale_provider.dart"
    documents, _, logic_sha = legal_resources(legal.read_text())
    sample_source = examples.read_text()
    function = sample_source.split("String _translatedExample", 1)[1].split("@override", 1)[0]
    samples = {match[1]: text_literal(match[2]) for match in re.finditer(r"case '([^']+)':\s*return\s+(" + STRING + r")\s*;", function)}
    fallback = list(re.finditer(r"default:\s*return\s+(" + STRING + r")\s*;", function))
    original = re.search(r"Text\((" + STRING + r"),\s*// i18n-allow: Original English", sample_source)
    if len(samples) != 11 or len(fallback) != 1 or original is None:
        raise ValueError("Expected the original 11 translation examples and English source")
    locale_source = locales.read_text().split("const kSupportedLocales = [", 1)[1].split("];", 1)[0]
    language_rows = []
    for match in re.finditer(r"\(Locale\(('([^']+)'(?:,\s*'([^']+)')?)\),\s*(" + STRING + r")\)", locale_source):
        language_rows.append({"languageCode": match[2], "countryCode": match[3], "nativeName": text_literal(match[4])})
    if len(language_rows) != 35:
        raise ValueError("Expected all 35 existing supported App locales")
    return {
        "legalDocuments": documents,
        "translationExamples": {"source": text_literal(original[1]), "translations": samples, "fallback": text_literal(fallback[0][1])},
        "supportedLocales": language_rows,
    }, logic_sha, {str(file.relative_to(mobile)): digest(file.read_bytes()) for file in [legal, examples, locales]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def dart_map(source, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*=\s*(?:<[^;{]+>)?\s*\{", source)
    if not match:
        raise ValueError(f"Dart map declaration not found: {name}")
    start = source.index("{", match.start())
    depth, quote, escaped = 0, None, False
    for index in range(start, len(source)):
        character = source[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in "\"'":
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if not depth:
                return ast.literal_eval(source[start:index + 1])
    raise ValueError(f"Unclosed Dart map: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile-root", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="Reproduce additional text after inline resources have been removed")
    args = parser.parse_args()
    mobile = args.mobile_root.resolve()
    workspace = Path(__file__).resolve().parent.parent
    original = mobile / "lib/features/chat/presentation/models/translation_language_options.dart"
    generated = mobile / "lib/generated/l10n/translation_language_names.dart"
    text = original.read_text()
    if re.search(r"_namesByDeviceLanguage\s*=\s*<", text):
        names = dart_map(text, "translationTargetNativeNames")
        localized = dart_map(text, "_namesByDeviceLanguage")
    else:
        text = generated.read_text()
        names = dart_map(text, "translationTargetNativeNames")
        localized = dart_map(text, "translationTargetNamesByDeviceLanguage")
    native_files = sorted(mobile.glob("ios/Runner/*.lproj/InfoPlist.strings"))
    native_files.append(mobile / "android/app/src/main/res/values/strings.xml")
    resources = []
    for file in native_files:
        raw = file.read_bytes()
        resources.append({"path": file.relative_to(mobile).as_posix(), "content": raw.decode("utf-8"), "sha256": digest(raw)})
    data = {
        "schemaVersion": 1,
        "sourceOwner": "chat-im-cs/lpp/lpp_mobile",
        "nativeNames": names,
        "localizedNames": localized,
        "nativeResources": resources,
    }
    out = workspace / "packages/im_l10n_catalog/catalog/mobile_supplemental/index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    baseline_file = workspace / "evidence/full-integration-mobile-baseline.json"
    if not baseline_file.exists():
        protected = native_files + [original, mobile / "ios/Runner/Info.plist", mobile / "pubspec.yaml", mobile / ".gitignore"]
        repo = mobile.parent.parent
        baseline = {
            "nativeNamesSha256": digest(canonical(names)),
            "localizedNamesSha256": digest(canonical(localized)),
            "targetLanguageCount": len(names),
            "deviceLanguageCount": len(localized),
            "localizedNameCount": sum(len(row) for row in localized.values()),
            "nativeResourceCount": len(resources),
            "sourceSha256": {file.relative_to(mobile).as_posix(): digest(file.read_bytes()) for file in protected},
            "gitBranch": subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip(),
            "gitStatusMobile": subprocess.check_output(["git", "status", "--porcelain=v1", "--", "lpp/lpp_mobile"], cwd=repo, text=True),
            "stagedMobileSha256": digest(subprocess.check_output(["git", "diff", "--cached", "--binary", "--", "lpp/lpp_mobile"], cwd=repo)),
        }
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n")
    baseline = json.loads(baseline_file.read_text())
    if args.baseline:
        extra = json.loads(args.baseline.read_text())["extendedResources"]
    else:
        extra, logic_sha, files_sha = additional_resources(mobile)
        if "extendedResources" not in baseline:
            baseline["extendedResources"] = extra
            baseline["legalPlatformLogicSha256"] = logic_sha
            baseline["additionalSourceSha256"] = files_sha
            baseline_file.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n")
    for name, value in extra.items():
        (out.parent / (name + ".json")).write_text(json.dumps({"schemaVersion": 1, "data": value}, ensure_ascii=False, indent=2) + "\n")
    print(f"Extracted {len(names)} target names, {sum(len(row) for row in localized.values())} localized names, {len(resources)} native files, {len(extra['supportedLocales'])} supported locale names, {len(extra['translationExamples']['translations'])} examples and {len(extra['legalDocuments']['documents'])} legal documents.")


if __name__ == "__main__":
    main()
