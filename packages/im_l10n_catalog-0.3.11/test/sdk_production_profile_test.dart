import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:im_l10n_catalog/im_l10n_catalog.dart';
import 'package:test/test.dart';

// These fingerprints describe the immutable 0.2.0 SDK profile. Adding languages
// must not replace its established public key order, metadata or 30 overrides.
const _legacyLocales = ['zh', 'zh_TW', 'en', 'ja', 'ko', 'vi'];
const _legacyKeysSha =
    '3ea59353e64162b57f4108b2b5cb5fa751fd09b65bba4371d1a0ac20ad1f375a';
const _legacyMetadataSha =
    '2d76ca6e2318e45d9d0315a2b21be410e4e4923d73e327e43fc27f5309142896';
const _legacyOverridesSha =
    '9df6b2f99799c272271a710771056eb3bc6ba1358c936a0649f6787cee91f9cd';

Map<String, dynamic> _read(File file) =>
    jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;

void _write(File file, Object value) {
  file.parent.createSync(recursive: true);
  file.writeAsStringSync('${jsonEncode(value)}\n');
}

Object? _canonical(Object? value) {
  if (value is Map) {
    final keys = value.keys.cast<String>().toList()..sort();
    return {for (final key in keys) key: _canonical(value[key])};
  }
  if (value is List) return value.map(_canonical).toList();
  return value;
}

String _fingerprint(Object? value) =>
    sha256.convert(utf8.encode(jsonEncode(_canonical(value)))).toString();

void main() {
  final packageRoot = Directory.current.absolute;
  final projectRoot = packageRoot.parent.parent;
  late Directory fixture;
  late Directory consumer;
  late Directory validationPackage;
  late Map<String, dynamic> index;
  late Map<String, dynamic> profile;
  late List<String> locales;
  late List<String> keys;
  late List<String> modules;
  late Map<String, Map<String, dynamic>> source;
  late Map<String, Map<String, dynamic>> generated;

  Map<String, dynamic> config({bool withProfile = true}) => {
        'schemaVersion': 1,
        'catalogVersion': index['packageVersion'],
        if (withProfile) 'profile': 'im_sdk',
        'locales': locales,
        'templateLocale': 'zh',
        'modules': withProfile ? modules : ['sdk'],
        'outputDir': 'lib/l10n',
        'outputClass': 'AppLocalizations',
        'layout': 'flat',
      };

  Map<String, Object?> validate(Directory destination) {
    _write(File('${destination.path}/l10n.bundle.json'),
        config(withProfile: false));
    return generateBundle(
        packageRoot: validationPackage, consumerRoot: destination);
  }

  setUpAll(() {
    final temporary =
        Directory('${projectRoot.path}/.codex-build/sdk-35-profile-contract')
          ..createSync(recursive: true);
    fixture = temporary.createTempSync('case_');
    consumer = Directory('${fixture.path}/consumer')..createSync();
    index = _read(File('${packageRoot.path}/catalog/index.json'));
    profile = _read(File('${packageRoot.path}/catalog/profiles/im_sdk.json'));
    locales = (index['locales'] as List).cast<String>();
    keys = (profile['keys'] as List).cast<String>();
    modules = (index['modules'] as Map).keys.cast<String>().toList();
    source = {};
    for (final locale in locales) {
      source[locale] = {};
      for (final module in modules) {
        source[locale]!.addAll(
            _read(File('${packageRoot.path}/catalog/$module/app_$locale.arb')));
      }
    }
    _write(File('${consumer.path}/l10n.bundle.json'), config());
    generateBundle(packageRoot: packageRoot, consumerRoot: consumer);
    generated = {
      for (final locale in locales)
        locale: _read(File('${consumer.path}/lib/l10n/app_$locale.arb')),
    };

    // Revalidate the generated production messages through the public strict
    // path. A profile preserves legacy metadata and deliberately bypasses that
    // path, so profile generation alone cannot prove placeholder agreement.
    validationPackage = Directory('${fixture.path}/validation_package')
      ..createSync();
    File('${validationPackage.path}/pubspec.yaml')
        .writeAsStringSync('version: ${index['packageVersion']}\n');
    _write(File('${validationPackage.path}/catalog/index.json'), {
      'schemaVersion': 1,
      'packageVersion': index['packageVersion'],
      'defaultLocale': 'zh',
      'locales': locales,
      'modules': {'sdk': keys},
    });
    for (final locale in locales) {
      _write(File('${validationPackage.path}/catalog/sdk/app_$locale.arb'),
          generated[locale]!);
    }
  });

  tearDownAll(() {
    if (fixture.existsSync()) fixture.deleteSync(recursive: true);
  });

  test('production SDK profile retains the immutable six-language contract',
      () {
    expect(profile['locales'], locales);
    expect(locales, hasLength(35));
    expect(keys, hasLength(1040));
    expect(_fingerprint(keys), _legacyKeysSha);
    expect(
        _fingerprint({
          for (final locale in _legacyLocales)
            locale: profile['overrides'][locale],
        }),
        _legacyOverridesSha);
    expect(
        _fingerprint({
          for (final locale in _legacyLocales)
            locale: profile['metadata'][locale],
        }),
        _legacyMetadataSha);
    final overrides = profile['overrides'] as Map;
    expect(overrides.keys, unorderedEquals(locales));
    expect(overrides.values.fold<int>(0, (n, row) => n + (row as Map).length),
        175);
  });

  test('new auth overrides retain SDK semantics with explicit English fallback',
      () {
    final newLocales =
        locales.where((locale) => !_legacyLocales.contains(locale)).toList();
    expect(profile['overrideFallbackLocaleByLocale'],
        {for (final locale in newLocales) locale: 'en'});
    final english = profile['overrides']['en'] as Map<String, dynamic>;
    expect(english, hasLength(5));
    for (final locale in newLocales) {
      final overrides = profile['overrides'][locale];
      expect(overrides, english, reason: locale);
      final summary = overrides['authQuickLoginSummary'] as String;
      expect(summary, isNot(contains('mouse')), reason: locale);
      expect(summary, isNot(contains('corp123123123')), reason: locale);
      expect(summary, isNot(contains('123123123')), reason: locale);
      expect(generated[locale]!['authQuickLoginSummary'], summary,
          reason: locale);
    }
  });

  test('new locale metadata retains exactly the selected shared source entries',
      () {
    for (final locale in locales.where((l) => !_legacyLocales.contains(l))) {
      final metadata = {
        for (final key in keys)
          if (source[locale]!.containsKey('@$key'))
            '@$key': source[locale]!['@$key'],
      };
      expect(profile['metadata'][locale], metadata, reason: locale);
      expect(metadata.keys,
          unorderedEquals(['@networkLatencyMs', '@diagnosticsEventCount']),
          reason: locale);
    }
  });

  test('production generation preserves 35 by 1040 values, order and metadata',
      () {
    for (final locale in locales) {
      final output = generated[locale]!;
      final outputKeys = output.keys.where((key) => !key.startsWith('@'));
      expect(output['@@locale'], locale);
      expect(outputKeys.toList(), keys, reason: locale);
      final overrides =
          profile['overrides'][locale] as Map<String, dynamic>? ?? {};
      final metadata = profile['metadata'][locale] as Map<String, dynamic>;
      for (final key in keys) {
        expect(output[key], overrides[key] ?? source[locale]![key],
            reason: '$locale/$key');
        expect(output.containsKey('@$key'), metadata.containsKey('@$key'),
            reason: '$locale/@$key');
        if (metadata.containsKey('@$key')) {
          expect(output['@$key'], metadata['@$key'], reason: '$locale/@$key');
        }
      }
    }
    expect(
        Directory('${consumer.path}/lib/l10n')
            .listSync()
            .whereType<File>()
            .where((file) => file.path.endsWith('.arb')),
        hasLength(35));
  });

  test('all production messages agree on ICU parameters and typed metadata',
      () {
    final destination = Directory('${fixture.path}/validated')..createSync();
    final receipt = validate(destination);
    expect(receipt['keys'], unorderedEquals(keys));
    expect(receipt['locales'], locales);
  });

  test('strict validation rejects a new language placeholder or type drift',
      () {
    final file = File('${validationPackage.path}/catalog/sdk/app_ar.arb');
    final original = file.readAsStringSync();
    final destination = Directory('${fixture.path}/invalid')..createSync();
    try {
      final invalidParameter = _read(file)
        ..['networkLatencyMs'] = '{unexpected}';
      _write(file, invalidParameter);
      expect(
          () => validate(destination),
          throwsA(isA<CatalogException>().having(
              (error) => error.message, 'message', contains('Placeholder'))));
      expect(Directory('${destination.path}/lib/l10n').existsSync(), isFalse);

      final invalidType = jsonDecode(original) as Map<String, dynamic>;
      invalidType['@networkLatencyMs']['placeholders']['ms']['type'] = 'String';
      _write(file, invalidType);
      expect(
          () => validate(destination),
          throwsA(isA<CatalogException>().having((error) => error.message,
              'message', contains('Placeholder type mismatch'))));
      expect(Directory('${destination.path}/lib/l10n').existsSync(), isFalse);
    } finally {
      file.writeAsStringSync(original);
    }
  });

  test('production check is repeatable and detects drift without rewriting it',
      () {
    final receipt = File('${consumer.path}/l10n.bundle.lock.json');
    final before = receipt.readAsBytesSync();
    generateBundle(
        packageRoot: packageRoot, consumerRoot: consumer, checkOnly: true);
    expect(receipt.readAsBytesSync(), before);
    final file = File('${consumer.path}/lib/l10n/app_ar.arb');
    final original = file.readAsStringSync();
    try {
      final changed = _read(file)..['commonConfirm'] = 'unmanaged edit';
      _write(file, changed);
      final changedBytes = file.readAsBytesSync();
      expect(
          () => generateBundle(
              packageRoot: packageRoot,
              consumerRoot: consumer,
              checkOnly: true),
          throwsA(isA<CatalogException>()));
      expect(file.readAsBytesSync(), changedBytes);
      expect(receipt.readAsBytesSync(), before);
    } finally {
      file.writeAsStringSync(original);
    }
  });
}
