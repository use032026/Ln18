#!/usr/bin/env python3
"""One-time extraction of IMSDK's static language data, without changing text.

After integration, --baseline can reproduce the resource files independently
of the original inline declarations. No backend or application state is read.
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STRING = r"r?'''[\s\S]*?'''|r?\"\"\"[\s\S]*?\"\"\"|r?'(?:\\.|[^'\\])*'|r?\"(?:\\.|[^\"\\])*\""
PATHS = {
    "chrome": "packages/im_sdk/lib/sdk/im_sdk_presentation.dart",
    "web": "web/src/presentation.ts",
    "names": "packages/im_sdk/lib/features/chat/presentation/models/translation_language_options.dart",
    "examples": "packages/im_sdk/lib/features/settings/presentation/pages/auto_translate_page.dart",
    "files": "packages/im_sdk/lib/features/chat/presentation/widgets/chat_input_toolbar.dart",
    "legal": "packages/im_sdk/lib/features/settings/presentation/pages/legal_document_page.dart",
    "supportedLocales": "packages/im_sdk/lib/core/providers/locale_provider.dart",
    "networkErrors": "packages/im_sdk/lib/core/network/error_handler.dart",
}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def text_literal(token):
    if token.startswith("r"):
        delimiter = token[1:4] if token[1:4] in ("'''", '"""') else token[1]
        return token[1 + len(delimiter):-len(delimiter)]
    return ast.literal_eval(token)


def object_literal(source, pattern):
    match = re.search(pattern, source)
    if match is None:
        raise ValueError("Original inline map is missing; use --baseline after integration")
    return ast.literal_eval(match.group(1).strip())


def language_returns(source):
    values = {}
    pattern = r"if\s*\(languageCode == '([^']+)'\)\s*(?:\{\s*)?return\s+(" + STRING + r")\s*;"
    for match in re.finditer(pattern, source):
        values[match[1]] = text_literal(match[2]).replace("$normalizedExtension", "{extension}")
    returns = list(re.finditer(r"return\s+(" + STRING + r")\s*;", source))
    if not returns:
        raise ValueError("Expected localized file message returns")
    values["zh"] = text_literal(returns[-1][1]).replace("$normalizedExtension", "{extension}")
    if set(values) != {"en", "ja", "ko", "vi", "zh"}:
        raise ValueError("File-message language structure changed: " + repr(set(values)))
    return values


def legal_platform_data(source):
    title_source = source.split("LegalDocumentData termsLegalDocumentForPlatform", 1)[1].split("LegalDocumentData _platformDocument", 1)[0]
    titles = [text_literal(match[0]) for match in re.finditer(STRING, title_source)]
    title_keys = ["termsAppBarIos", "termsAppBarAndroid", "termsTitleIos", "termsTitleAndroid", "privacyAppBarIos", "privacyTitleIos"]
    if len(titles) != len(title_keys):
        raise ValueError("Legal platform title structure changed")
    body = source.split("String? _platformizeLegalText", 1)[1].split("\n  return text;", 1)[0]
    clauses, suffixes = {}, {}
    for match in re.finditer(r"if \(text.startsWith\((" + STRING + r")\)\) \{(.*?)\n  \}", body, re.S):
        prefix = text_literal(match[1])
        values = [text_literal(token[0]) for token in re.finditer(STRING, match[2])]
        if "text.replaceFirst" in match[2]:
            if len(values) != 4 or values[0] != values[2]:
                raise ValueError("Legal platform suffix structure changed")
            suffixes = {"ios": values[1], "android": values[3]}
        elif len(values) == 2:
            clauses[prefix] = dict(zip(["ios", "android"], values))
        elif len(values) == 1 and "? null" in re.sub(r"\s+", " ", match[2]):
            clauses[prefix] = {"android": values[0]}
        else:
            raise ValueError("Legal platform clause structure changed: " + prefix)
    if len(clauses) != 16 or set(suffixes) != {"ios", "android"}:
        raise ValueError("Expected 16 legal platform clauses and two display suffixes")
    failure = re.search(r"SnackBar\(content:\s*(?:const )?Text\((" + STRING + r")", source)
    official = re.search(r"label:\s*(?:const )?Text\((" + STRING + r")", source)
    if failure is None or official is None:
        raise ValueError("Legal viewer display text is missing")
    return {"titles": dict(zip(title_keys, titles)), "clauses": clauses, "suffixes": suffixes,
            "chrome": {"openFailed": text_literal(failure[1]), "viewOfficial": text_literal(official[1])}}


def supported_locale_data(source):
    block = re.search(r"const kSupportedLocales = \[(.*?)\n\];", source, re.S)
    if block is None:
        raise ValueError("Original supported-locale display list is missing")
    values = []
    for match in re.finditer(r"\(Locale\((" + STRING + r")(?:,\s*(" + STRING + r"))?\),\s*(" + STRING + r")\)", block[1]):
        values.append({"languageCode": text_literal(match[1]), "countryCode": text_literal(match[2]) if match[2] else None, "label": text_literal(match[3])})
    if len(values) != 6:
        raise ValueError("Expected the SDK's existing six supported locale labels")
    return values


def network_error_data(source):
    pattern = r"_localizedByLocale\(\s*l10n,\s*((?:(?:zh|zhTw|en|ja|ko|vi):\s*(?:" + STRING + r")\s*,\s*)+)\)"
    messages, calls = {}, 0
    for match in re.finditer(pattern, source):
        fields = {item[1]: text_literal(item[2]) for item in re.finditer(r"(zh|zhTw|en|ja|ko|vi):\s*(" + STRING + r")\s*,", match[1])}
        if set(fields) != {"zh", "zhTw", "en", "ja", "ko", "vi"}:
            raise ValueError("Network error translation fields changed")
        if fields["zh"] in messages and messages[fields["zh"]] != fields:
            raise ValueError("Network source phrase has conflicting translations")
        messages[fields["zh"]] = fields
        calls += 1
    if len(messages) != 12 or calls != 14:
        raise ValueError("Expected 12 six-language network messages at 14 call sites")
    return messages


def extract(sdk):
    source = {key: (sdk / relative).read_text() for key, relative in PATHS.items()}
    chrome = object_literal(source["chrome"], r"const _sdkTranslations = <String, List<String>>(\{[\s\S]*?\n\});")
    web = object_literal(source["web"], r"const catalog:[^=]+=(\s*\{[\s\S]*?\n\});")
    native = object_literal(source["names"], r"const translationTargetNativeNames = <String, String>(\{[\s\S]*?\n\});")
    names = object_literal(source["names"], r"const _namesByDeviceLanguage = <String, Map<String, String>>(\{[\s\S]*?\n\});")
    example_function = source["examples"].split("String _translatedExample", 1)[1].split("@override", 1)[0]
    examples = {match[1]: text_literal(match[2]) for match in re.finditer(r"case '([^']+)':\s*return\s+(" + STRING + r")\s*;", example_function)}
    if len(examples) != 11:
        raise ValueError("Expected 11 target-language examples")
    file_source = source["files"]
    pick = file_source.split("String _filePickFailedText", 1)[1].split("String _fileValidationErrorText", 1)[0]
    validation = file_source.split("String _fileValidationErrorText", 1)[1].split("String _unsupportedFileTypeText", 1)[0]
    sections = {}
    branch_names = ["mediaUsePhotos", "unrecognizedType", "typeMismatch"]
    for index, name in enumerate(branch_names):
        start = validation.index("if (rejection == ChatFileAttachmentRejection." + name + ")")
        end = validation.index("if (rejection == ChatFileAttachmentRejection." + branch_names[index + 1] + ")") if index + 1 < len(branch_names) else validation.index("final normalizedExtension")
        sections[name] = language_returns(validation[start:end])
    extension_section = validation.split("final normalizedExtension", 1)[1]
    unsupported = file_source.split("String _unsupportedFileTypeText", 1)[1].split("void _insertEmoji", 1)[0]
    files = {"filePickFailed": language_returns(pick), **sections,
             "unsupportedExtension": language_returns(extension_section), "unsupportedType": language_returns(unsupported)}
    documents = {}
    for match in re.finditer(r"const (\w+) = LegalDocumentData\((.*?)\n\);", source["legal"], re.S):
        title = re.search(r"appBarTitle:\s*(" + STRING + r")\s*,", match[2])
        blocks = [text_literal(item[1]) for item in re.finditer(r"LegalDocumentBlock\(\s*(" + STRING + r")\s*\)", match[2])]
        if title is None or not blocks:
            raise ValueError("Unable to parse legal document: " + match[1])
        documents[match[1]] = {"appBarTitle": text_literal(title[1]), "blocks": blocks}
    if len(documents) != 13:
        raise ValueError("Expected 13 unchanged legal-document resources")
    return {
        "schemaVersion": 1,
        "chrome": {"columns": ["zh_TW", "en", "ja", "ko", "vi"], "messages": chrome},
        "web": {"columns": ["zh-TW", "en", "ja", "ko", "vi"], "messages": web},
        "languageNames": {"native": native, "byDeviceLanguage": names},
        "examples": examples,
        "fileMessages": files,
        "legalDocuments": documents,
        "legalPlatformMessages": legal_platform_data(source["legal"]),
        "supportedLocales": supported_locale_data(source["supportedLocales"]),
        "networkErrors": network_error_data(source["networkErrors"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=Path("/Users/starburst/Desktop/IMSDK"))
    parser.add_argument("--package-root", type=Path, default=ROOT / "packages/im_l10n_catalog")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    sdk = args.sdk_root.resolve()
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        resources = baseline["resources"]
        if "legalPlatformMessages" not in resources:
            # Extend the migration baseline from its exact recorded Git source,
            # never from already-generated resources or modified display text.
            original = subprocess.check_output(["git", "-C", str(sdk), "show", baseline["gitHead"] + ":" + PATHS["legal"]])
            expected = baseline["sourceSha256"][PATHS["legal"]]
            if hashlib.sha256(original).hexdigest() != expected:
                raise ValueError("Recorded legal source differs from baseline Git source")
            resources["legalPlatformMessages"] = legal_platform_data(original.decode())
            baseline["legalPlatformSourceSha256"] = expected
            save(args.baseline, baseline)
        for name, extractor in [("supportedLocales", supported_locale_data), ("networkErrors", network_error_data)]:
            if name not in resources:
                original = subprocess.check_output(["git", "-C", str(sdk), "show", baseline["gitHead"] + ":" + PATHS[name]])
                current = (sdk / PATHS[name]).read_bytes()
                if current != original:
                    raise ValueError("Newly inventoried source differs from baseline commit: " + PATHS[name])
                resources[name] = extractor(original.decode())
                baseline["sourceSha256"][PATHS[name]] = hashlib.sha256(original).hexdigest()
                save(args.baseline, baseline)
    else:
        resources = extract(sdk)
        baseline = {
            "capturedOn": "2026-10-29", "gitHead": subprocess.check_output(["git", "-C", str(sdk), "rev-parse", "HEAD"], text=True).strip(),
            "gitStatus": subprocess.check_output(["git", "-C", str(sdk), "status", "--porcelain=v1"], text=True),
            "sourceSha256": {relative: hashlib.sha256((sdk / relative).read_bytes()).hexdigest() for relative in PATHS.values()},
            "resources": resources,
        }
        save(ROOT / "evidence/full-integration-sdk-baseline.json", baseline)
    target = args.package_root.resolve() / "catalog/sdk_supplemental"
    for name in ["chrome", "web", "languageNames", "examples", "fileMessages", "legalDocuments", "legalPlatformMessages", "supportedLocales", "networkErrors"]:
        save(target / (name + ".json"), {"schemaVersion": 1, "data": resources[name]})
    counts = {"sdkChrome": len(resources["chrome"]["messages"]), "webChrome": len(resources["web"]["messages"]),
              "nativeLanguageNames": len(resources["languageNames"]["native"]),
              "deviceLanguageNames": sum(len(v) for v in resources["languageNames"]["byDeviceLanguage"].values()),
              "examples": len(resources["examples"]), "fileMessageGroups": len(resources["fileMessages"]),
              "legalDocuments": len(resources["legalDocuments"]),
              "legalBlocks": sum(len(v["blocks"]) for v in resources["legalDocuments"].values()),
              "legalPlatformClauses": len(resources["legalPlatformMessages"]["clauses"]),
              "legalPlatformDisplayValues": sum(len(v) for v in resources["legalPlatformMessages"]["clauses"].values()) + len(resources["legalPlatformMessages"]["titles"]) + len(resources["legalPlatformMessages"]["suffixes"]) + len(resources["legalPlatformMessages"]["chrome"])}
    counts.update({"supportedLocaleLabels": len(resources["supportedLocales"]), "networkErrorMessages": len(resources["networkErrors"]), "networkErrorTranslatedValues": sum(len(v) for v in resources["networkErrors"].values())})
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
