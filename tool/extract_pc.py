#!/usr/bin/env python3
"""One-time extraction of PC locale objects using its existing TypeScript toolchain.

The TypeScript files are transpiled in memory and have no business/runtime
imports. Normal generation reads the resulting catalog and never imports this
source project again.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


LOCALE_EXPORTS = {
    "zh-CN": "zhCN", "zh-TW": "zhTW", "en": "en", "ja": "ja", "vi": "vi", "th": "th",
}

NODE_EXTRACT = r"""
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
const cache = new Map();
function load(file) {
  file = path.resolve(file);
  if (cache.has(file)) return cache.get(file);
  const exports = {};
  cache.set(file, exports);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  new Function('exports', 'require', code)(exports, (specifier) => {
    if (specifier !== './workbench-fallback') throw new Error('Unexpected resource import: ' + specifier);
    return load(path.resolve(path.dirname(file), specifier + '.ts'));
  });
  return exports;
}
const localeExports = {'zh-CN':'zhCN','zh-TW':'zhTW',en:'en',ja:'ja',vi:'vi',th:'th'};
const base = 'src/renderer/i18n/messages';
const locales = Object.fromEntries(Object.entries(localeExports).map(([locale, symbol]) => [locale, load(`${base}/${locale}.ts`)[symbol]]));
const fallbacks = load(`${base}/workbench-fallback.ts`);
process.stdout.write(JSON.stringify({ locales, fallbacks }));
"""


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def flatten(value, prefix=""):
    if isinstance(value, str):
        return {prefix: value}
    entries = enumerate(value) if isinstance(value, list) else value.items()
    result = {}
    for key, item in entries:
        result.update(flatten(item, f"{prefix}.{key}" if prefix else str(key)))
    return result


def shape(value):
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return [shape(item) for item in value]
    return {key: shape(item) for key, item in value.items()}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc-root", type=Path, required=True)
    args = parser.parse_args()
    pc = args.pc_root.resolve()
    root = Path(__file__).resolve().parent.parent
    output = root / "packages/im_l10n_catalog/catalog/pc"
    result = subprocess.run(["node", "--input-type=module", "-"], input=NODE_EXTRACT, text=True, cwd=pc,
                            capture_output=True, check=True)
    data = json.loads(result.stdout)
    locales, fallbacks = data["locales"], data["fallbacks"]
    modules = list(locales["zh-CN"])
    baseline = {"scope": "PC translation resources only; no runtime or business changes", "locales": {}, "sourceSha256": {}}
    for locale, dictionary in locales.items():
        if set(dictionary) != set(modules):
            raise ValueError(f"Module mismatch: {locale}")
        leaves = flatten(dictionary)
        baseline["locales"][locale] = {"keys": len(leaves), "modules": len(modules), "leafSha256": canonical_hash(leaves),
                                         "objectSha256": canonical_hash(dictionary),
                                         "orderedObjectSha256": hashlib.sha256(json.dumps(dictionary, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
                                         "shape": shape(dictionary)}
        for module in modules:
            save(output / locale / f"{module}.json", dictionary[module])
    save(output / "index.json", {"schemaVersion": 1, "locales": list(LOCALE_EXPORTS), "exports": LOCALE_EXPORTS,
                                  "modules": modules, "moduleOrder": {locale: list(data) for locale, data in locales.items()},
                                  "defaultLocale": "zh-CN", "fallbackExports": list(fallbacks)})
    save(output / "fallbacks.json", fallbacks)
    for file in sorted((pc / "src/renderer/i18n/messages").glob("*.ts")):
        baseline["sourceSha256"][str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
    baseline["fallbacksSha256"] = canonical_hash(fallbacks)
    default_leaves = flatten(locales["zh-CN"])
    def parameters(text):
        return sorted(set(re.findall(r"\{(\w+)\}", text)))
    baseline["preservedParameterDifferences"] = {
        locale: [{"key": key, "default": parameters(default_leaves[key]), "localized": parameters(text)}
                 for key, text in flatten(dictionary).items() if parameters(text) != parameters(default_leaves[key])]
        for locale, dictionary in locales.items()
    }
    save(root / "evidence/full-integration-pc-baseline.json", baseline)
    print(f"Extracted PC: {len(locales)} locales, {len(modules)} modules, {len(flatten(locales['zh-CN']))} leaves per locale")


if __name__ == "__main__":
    main()
