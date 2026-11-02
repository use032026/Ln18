"""Render the PC consumer's existing TypeScript resource interface."""
import json
from pathlib import Path


HEADER = "// Generated from im_l10n_catalog 0.3.3. Edit the public catalog, not this file.\n"
TYPE_DEFINITION = """
type WidenMessageLeaves<T> = T extends string
  ? string
  : T extends readonly (infer Item)[]
    ? readonly WidenMessageLeaves<Item>[]
    : {
        [Key in keyof T]: WidenMessageLeaves<T[Key]>;
      };

export type MessageDictionary = WidenMessageLeaves<typeof zhCN>;
"""


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_tree(value, location):
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_tree(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_tree(item, f"{location}.{key}")
        return
    raise ValueError(f"PC translation must be text, array or object: {location}")


def render(package_root: Path, consumer_root: Path, config: dict) -> dict[str, str]:
    catalog = package_root / "catalog/pc"
    index = _json(catalog / "index.json")
    locales, modules = index["locales"], index["modules"]
    # This first production migration retains the existing consumer contract.
    # Locale/module changes require coordinated edits to the consumer itself.
    for field, expected in [("locales", locales), ("modules", modules)]:
        if field in config and config[field] != expected:
            raise ValueError(f"PC {field} must preserve the current consumer contract")
    output = {}
    for locale in locales:
        module_order = index["moduleOrder"][locale]
        if set(module_order) != set(modules):
            raise ValueError(f"PC module order does not match module index: {locale}")
        dictionary = {module: _json(catalog / locale / f"{module}.json") for module in module_order}
        _validate_tree(dictionary, locale)
        symbol = index["exports"][locale]
        text = json.dumps(dictionary, ensure_ascii=False, indent=2)
        if locale == index["defaultLocale"]:
            source = HEADER + f"export const {symbol} = {text} as const;\n" + TYPE_DEFINITION
        else:
            source = HEADER + "import type { MessageDictionary } from './zh-CN';\n\n" + f"export const {symbol}: MessageDictionary = {text};\n"
        output[f"src/renderer/i18n/messages/{locale}.ts"] = source
    fallbacks = _json(catalog / "fallbacks.json")
    _validate_tree(fallbacks, "fallbacks")
    output["src/renderer/i18n/messages/workbench-fallback.ts"] = HEADER + "\n".join(
        f"export const {symbol} = {json.dumps(fallbacks[symbol], ensure_ascii=False, indent=2)};\n"
        for symbol in index["fallbackExports"]
    )
    names = _json(catalog / "displayNames.json")
    if names.get("schemaVersion") != 1:
        raise ValueError("Unsupported PC display-name schema")
    _validate_tree(names["localeLabels"], "PC locale labels")
    _validate_tree(names["autoTranslateTargetLanguageLabels"], "PC translation target labels")
    if set(names["localeLabels"]) != set(locales):
        raise ValueError("PC display names must match supported locales")
    output["src/shared/generated/l10n/pc-display-names.ts"] = (
        HEADER + "export const pcLocaleLabels = "
        + json.dumps(names["localeLabels"], ensure_ascii=False, indent=2) + " as const;\n\n"
        + "export const pcAutoTranslateTargetLanguageLabels = "
        + json.dumps(names["autoTranslateTargetLanguageLabels"], ensure_ascii=False, indent=2) + " as const;\n"
    )
    return output
