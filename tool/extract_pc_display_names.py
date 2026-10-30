#!/usr/bin/env python3
"""One-time PC language-name extraction through its existing TypeScript parser."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


NODE_EXTRACT = r"""
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
const allowed = new Set([
  path.resolve('src/renderer/i18n/locales.ts'),
  path.resolve('src/renderer/data/settings/auto-translate-settings.ts'),
  path.resolve('src/shared/generated/l10n/pc-display-names.ts'),
]);
const cache = new Map();
function load(file) {
  file = path.resolve(file);
  if (!allowed.has(file)) throw new Error('Unexpected resource import: ' + file);
  if (cache.has(file)) return cache.get(file);
  const exports = {};
  cache.set(file, exports);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  new Function('exports', 'require', code)(exports, (specifier) => load(path.resolve(path.dirname(file), specifier + '.ts')));
  return exports;
}
const app = load('src/renderer/i18n/locales.ts');
const targets = load('src/renderer/data/settings/auto-translate-settings.ts');
process.stdout.write(JSON.stringify({
  localeLabels: app.localeLabels,
  autoTranslateTargetLanguageLabels: targets.autoTranslateTargetLanguageLabels,
  supportedLocales: app.supportedLocales,
  defaultLocale: app.defaultLocale,
  autoTranslateTargetLanguages: targets.autoTranslateTargetLanguages,
  defaultAutoTranslateTargetLanguage: targets.defaultAutoTranslateTargetLanguage,
}));
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    pc = args.pc_root.resolve()
    result = subprocess.run(["node", "--input-type=module", "-"], cwd=pc, input=NODE_EXTRACT,
                            text=True, capture_output=True, check=True)
    data = json.loads(result.stdout)
    if len(data["localeLabels"]) != 6 or len(data["autoTranslateTargetLanguageLabels"]) != 11:
        raise ValueError("Expected six PC locales and eleven translation target labels")
    baseline = root / "evidence/full-integration-pc-display-baseline.json"
    if not baseline.exists():
        sources = ["src/renderer/i18n/locales.ts", "src/renderer/data/settings/auto-translate-settings.ts"]
        baseline.write_text(json.dumps({"data": data, "sourceSha256": {
            path: hashlib.sha256((pc / path).read_bytes()).hexdigest() for path in sources
        }}, ensure_ascii=False, indent=2) + "\n")
    target = root / "packages/im_l10n_catalog/catalog/pc/displayNames.json"
    target.write_text(json.dumps({"schemaVersion": 1, "localeLabels": data["localeLabels"],
                                 "autoTranslateTargetLanguageLabels": data["autoTranslateTargetLanguageLabels"]},
                                ensure_ascii=False, indent=2) + "\n")
    print("Extracted 6 PC locale labels and 11 translation target labels")


if __name__ == "__main__":
    main()
