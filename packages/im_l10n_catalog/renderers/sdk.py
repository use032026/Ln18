"""Render IMSDK's selected, immutable supplementary language resources.

The generated data preserves the SDK's own wording and fallback order. It
contains no translation engine or application/network state.
"""
import json
import re
from pathlib import Path


def _load(package_root, name):
    document = json.loads((package_root / "catalog/sdk_supplemental" / (name + ".json")).read_text())
    if document.get("schemaVersion") != 1:
        raise ValueError("Unsupported SDK resource schema: " + name)
    return document["data"]


def _dart(value):
    # JSON literals are also Dart literals for these string-only data tables.
    # Dart interpolation must be escaped; the stored resource stays unchanged.
    return json.dumps(value, ensure_ascii=False, indent=2).replace("$", r"\$")


def expand_supplemental(package_root: Path):
    """Resolve reviewed shared keys for new locales without changing old values.

    SDK-only phrases have an explicit English fallback. ARB ICU programs are
    never copied into the Web's simple placeholder replacement at runtime.
    """
    index = json.loads((package_root / "catalog/index.json").read_text())
    profile = json.loads((package_root / "catalog/profiles/im_sdk.json").read_text())
    locales = index["locales"]
    original = ["zh", "zh_TW", "en", "ja", "ko", "vi"]
    if locales[:6] != original or len(locales) != len(set(locales)):
        raise ValueError("SDK locale expansion must retain the original locale prefix")
    added = [locale for locale in locales if locale not in original]
    mappings = _load(package_root, "sharedMappings")
    tables = {name: _load(package_root, name) for name in ["chrome", "web", "fileMessages", "networkErrors"]}
    cached = {}

    def shared(mapping, locale, source):
        module, key = mapping["module"], mapping["key"]
        if module not in index["modules"] or key not in index["modules"][module]:
            raise ValueError(f"Unknown shared SDK mapping: {module}.{key}")
        identity = (module, locale)
        if identity not in cached:
            cached[identity] = json.loads((package_root / f"catalog/{module}/app_{locale}.arb").read_text())
        overrides = profile.get("overrides", {}).get(locale, {})
        value = overrides.get(key, cached[identity].get(key))
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Empty shared SDK translation: {module}.{key}/{locale}")
        if re.search(r"\{\s*\w+\s*,", value):
            raise ValueError(f"SDK chrome cannot execute ICU programs: {module}.{key}/{locale}")
        wrapper = mapping.get("wrapper", "{value}")
        if wrapper.count("{value}") != 1:
            raise ValueError("SDK translation wrapper needs one value slot")
        value = wrapper.replace("{value}", value)
        if set(re.findall(r"\{(\w+)\}", source)) != set(re.findall(r"\{(\w+)\}", value)):
            raise ValueError(f"SDK placeholder mismatch: {module}.{key}/{locale}")
        return value, "sdkProfileOverride" if key in overrides else "sharedArb"

    expanded, coverage = {}, {}
    for name, data in tables.items():
        messages = data["messages"] if name in {"chrome", "web"} else data
        if set(mappings.get(name, {})) - set(messages):
            raise ValueError("SDK mapping refers to an unknown source key: " + name)
        if name in {"chrome", "web"}:
            expected = ["zh_TW", "en", "ja", "ko", "vi"] if name == "chrome" else ["zh-TW", "en", "ja", "ko", "vi"]
            if data["columns"] != expected or any(len(values) != 5 for values in messages.values()):
                raise ValueError("Existing SDK chrome rows and their five columns must remain immutable")
        output, fallback, origins = {}, {}, {}
        for source, values in messages.items():
            old_english = values[1] if name in {"chrome", "web"} else values["en"]
            current = list(values) if isinstance(values, list) else dict(values)
            for locale in added:
                if source in mappings.get(name, {}):
                    value, origin = shared(mappings[name][source], locale, old_english)
                else:
                    value, origin = old_english, "englishFallback"
                    fallback[source] = old_english
                origins.setdefault(locale, {}).setdefault(origin, []).append(source)
                if isinstance(current, list):
                    current.append(value)
                else:
                    current[locale] = value
            output[source] = current
        expanded[name] = output
        coverage[name] = {
            "sourceKeyCount": len(messages),
            "sharedMappings": mappings.get(name, {}),
            "englishFallbackValues": fallback,
            "newLocaleCoverage": {locale: {origin: len(keys) for origin, keys in by_origin.items()} for locale, by_origin in origins.items()},
        }
    columns = locales[1:]
    report = {
        "schemaVersion": 1, "localeCount": len(locales), "originalLocalesPreserved": original,
        "newLocales": added, "translatedColumnLocales": columns,
        "policy": "Existing six-language values are unchanged. Only reviewed shared keys are localized for new locales; unmapped SDK phrases use their existing English value, not an invented translation.",
        "tables": coverage,
        "profileOverrides": {
            key: {
                "newLocaleValues": {locale: profile.get("overrides", {}).get(locale, {}).get(key) for locale in added},
                "newLocaleOrigins": {
                    locale: "sdkEnglishFallback" if profile.get("overrides", {}).get(locale, {}).get(key) == profile.get("overrides", {}).get("en", {}).get(key)
                    else "sdkLocalizedOverride" if key in profile.get("overrides", {}).get(locale, {}) else "missingSdkOverride"
                    for locale in added
                },
            }
            for key in sorted(set().union(*(set(values) for values in profile.get("overrides", {}).values())))
        },
        "legalAndExamples": "Existing document bodies, examples and their existing fallback logic are unchanged. No 35-language legal translation is claimed.",
    }
    return expanded, columns, report


def render(package_root: Path, consumer_root: Path, config: dict) -> dict[str, str]:
    expanded, columns, coverage = expand_supplemental(package_root)
    names = _load(package_root, "languageNames")
    examples = _load(package_root, "examples")
    files = expanded["fileMessages"]
    documents = _load(package_root, "legalDocuments")
    legal_platform = _load(package_root, "legalPlatformMessages")
    supported_locales = _load(package_root, "supportedLocales")
    network_errors = expanded["networkErrors"]
    version = config["catalogVersion"]
    header = f"// Generated by im_l10n_catalog {version}. Do not edit.\n"
    dart = header + "import 'package:flutter/widgets.dart' show Locale;\n\n"
    dart += "const sdkChromeLocales = <String>" + _dart(columns) + ";\n\n"
    for name, kind, value in [
        ("sdkChromeTranslations", "<String, List<String>>", expanded["chrome"]),
        ("translationTargetNativeNames", "<String, String>", names["native"]),
        ("translationNamesByDeviceLanguage", "<String, Map<String, String>>", names["byDeviceLanguage"]),
        ("translationExampleMessages", "<String, String>", examples),
        ("sdkFileAttachmentMessages", "<String, Map<String, String>>", files),
        ("sdkNetworkErrorMessages", "<String, Map<String, String>>", network_errors),
    ]:
        dart += f"const {name} = {kind}" + _dart(value) + ";\n\n"
    dart += "const sdkSupportedLocales = <(Locale, String)>[\n"
    for locale in supported_locales:
        arguments = _dart(locale["languageCode"])
        if locale["countryCode"] is not None:
            arguments += ", " + _dart(locale["countryCode"])
        dart += "  (Locale(" + arguments + "), " + _dart(locale["label"]) + "),\n"
    dart += "];\n"
    legal = header + "part of 'package:im_sdk/features/settings/presentation/pages/legal_document_page.dart';\n\n"
    legal += "const sdkLegalTitles = <String, String>" + _dart(legal_platform["titles"]) + ";\n\n"
    legal += "const sdkLegalPlatformClauses = <String, Map<String, String>>" + _dart(legal_platform["clauses"]) + ";\n\n"
    legal += "const sdkLegalPlatformSuffixes = <String, String>" + _dart(legal_platform["suffixes"]) + ";\n\n"
    legal += "const sdkLegalOpenFailed = " + _dart(legal_platform["chrome"]["openFailed"]) + ";\n"
    legal += "const sdkLegalViewOfficial = " + _dart(legal_platform["chrome"]["viewOfficial"]) + ";\n\n"
    for name, document in documents.items():
        if not name.isidentifier():
            raise ValueError("Invalid legal resource declaration name")
        legal += f"const {name} = LegalDocumentData(\n  appBarTitle: " + _dart(document["appBarTitle"]) + ",\n  blocks: [\n"
        legal += "".join("    LegalDocumentBlock(" + _dart(block) + "),\n" for block in document["blocks"])
        legal += "  ],\n);\n\n"
    web_columns = ["pt-BR" if locale == "pt" else locale.replace("_", "-") for locale in columns]
    typescript = header + "export const sdkUiLocales = " + json.dumps(web_columns, ensure_ascii=False) + " as const;\n\n"
    typescript += "export const sdkUiCatalog: Record<string, readonly string[]> = " + json.dumps(expanded["web"], ensure_ascii=False, indent=2) + ";\n"
    return {
        "packages/im_sdk/lib/generated/l10n/sdk_resources.dart": dart,
        "packages/im_sdk/lib/generated/l10n/sdk_legal_documents.g.dart": legal,
        "web/src/generated/l10n/sdk_catalog.ts": typescript,
        "packages/im_sdk/lib/generated/l10n/sdk_coverage.json": json.dumps({"generatedBy": "im_l10n_catalog", "catalogVersion": version, **coverage}, ensure_ascii=False, indent=2) + "\n",
    }
