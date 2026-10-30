import 'dart:convert';
import 'dart:io';

import 'package:im_l10n_catalog/im_l10n_catalog.dart';
import 'package:test/test.dart';

void main() {
  late Directory fixture;
  late Directory catalog;
  late Directory app;
  late Map<String, dynamic> config;
  late Map<String, dynamic> index;

  void jsonFile(String path, Object object) {
    final file = File(path)..parent.createSync(recursive: true);
    file.writeAsStringSync(jsonEncode(object));
  }

  Map<String, dynamic> read(String path) =>
      jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;

  void writeConfig() => jsonFile('${app.path}/l10n.bundle.json', config);
  Map<String, Object?> generate() {
    writeConfig();
    return generateBundle(packageRoot: catalog, consumerRoot: app);
  }

  Matcher failsWith(String text) => throwsA(
        isA<CatalogException>().having(
          (error) => error.message,
          'message',
          contains(text),
        ),
      );

  setUp(() {
    final fixtures = Directory('.dart_tool/catalog_test_fixtures')
      ..createSync(recursive: true);
    fixture = fixtures.createTempSync('case_');
    catalog = Directory('${fixture.path}/catalog_package')..createSync();
    app = Directory('${fixture.path}/app')..createSync();
    File('${catalog.path}/pubspec.yaml').writeAsStringSync('version: 0.1.0\n');
    index = {
      'schemaVersion': 1,
      'packageVersion': '0.1.0',
      'defaultLocale': 'zh',
      'locales': ['zh', 'en'],
      'modules': {
        'common': ['commonConfirm', 'commonDelete'],
        'auth': ['authLoginButton'],
        'chat': ['chatReadCount', 'chatNewMessages'],
      },
    };
    jsonFile('${catalog.path}/catalog/index.json', index);
    for (final locale in ['zh', 'en']) {
      jsonFile('${catalog.path}/catalog/common/app_$locale.arb', {
        '@@locale': locale,
        'commonConfirm': locale == 'en' ? 'OK' : '确定',
        'commonDelete': locale == 'en' ? 'Delete' : '删除',
      });
      jsonFile('${catalog.path}/catalog/auth/app_$locale.arb', {
        '@@locale': locale,
        'authLoginButton': locale == 'en' ? 'Sign In' : '登录',
      });
      jsonFile('${catalog.path}/catalog/chat/app_$locale.arb', {
        '@@locale': locale,
        'chatReadCount': locale == 'en' ? 'Read by {count}' : '已读 {count} 人',
        'chatNewMessages': locale == 'en'
            ? '{count, plural, one {Ready} other {{count} messages}}'
            : '{count, plural, other {{count} 条消息}}',
        for (final key in ['chatReadCount', 'chatNewMessages'])
          '@$key': {
            'description': 'Fixture parameter contract',
            'placeholders': {
              'count': {'type': 'int'},
            },
          },
      });
    }
    config = {
      'schemaVersion': 1,
      'catalogVersion': '0.1.0',
      'locales': ['en'],
      'templateLocale': 'en',
      'modules': ['common', 'chat'],
      'excludeKeys': ['commonDelete'],
      'overridesDir': 'l10n_overrides',
      'outputDir': 'lib/l10n',
      'outputClass': 'DemoLocalizations',
    };
  });

  tearDown(() {
    if (fixture.existsSync()) fixture.deleteSync(recursive: true);
  });

  test('selects language/module/key and preserves typed ICU metadata', () {
    jsonFile('${app.path}/l10n_overrides/en.json', {
      'commonConfirm': 'Confirm',
    });
    final receipt = generate();
    final output = read('${app.path}/lib/l10n/arb/app_en.arb');
    expect(output['commonConfirm'], 'Confirm');
    expect(output, isNot(contains('authLoginButton')));
    expect(output, isNot(contains('commonDelete')));
    expect(File('${app.path}/lib/l10n/arb/app_zh.arb').existsSync(), isFalse);
    expect(
      output['chatNewMessages'],
      '{count, plural, one {Ready} other {{count} messages}}',
    );
    expect(output['@chatReadCount']['placeholders']['count']['type'], 'int');
    expect(receipt['overrides'], {
      'en': ['commonConfirm'],
    });
    expect(receipt['catalogVersion'], '0.1.0');
    final yaml = File('${app.path}/l10n.yaml').readAsStringSync();
    expect(yaml, contains('output-class: DemoLocalizations'));
    expect(yaml, contains('template-arb-file: app_en.arb'));
    expect(yaml, isNot(contains('synthetic-package')));
  });

  test(
    'reads parameter metadata from default locale when only en is selected',
    () {
      final path = '${catalog.path}/catalog/chat/app_en.arb';
      final en = read(path)
        ..removeWhere((key, _) => key.startsWith('@') && key != '@@locale');
      jsonFile(path, en);
      generate();
      final output = read('${app.path}/lib/l10n/arb/app_en.arb');
      expect(output['@chatReadCount']['placeholders']['count']['type'], 'int');
    },
  );

  test('supports a key allowlist within selected modules', () {
    config['includeKeys'] = ['commonConfirm'];
    config['excludeKeys'] = <String>[];
    final receipt = generate();
    expect(receipt['keys'], ['commonConfirm']);
  });

  test('regeneration removes old locales and old generated Dart', () {
    config['locales'] = ['en', 'zh'];
    generate();
    final generated = Directory('${app.path}/lib/l10n/generated')..createSync();
    File(
      '${generated.path}/app_localizations_zh.dart',
    ).writeAsStringSync('// generated');
    config['locales'] = ['en'];
    final first = generate();
    expect(File('${app.path}/lib/l10n/arb/app_zh.arb').existsSync(), isFalse);
    expect(generated.existsSync(), isFalse);
    expect(generate()['bundleSha256'], first['bundleSha256']);
  });

  test('rejects catalog and pubspec version drift', () {
    config['catalogVersion'] = '0.2.0';
    expect(generate, failsWith('Version mismatch'));
    config['catalogVersion'] = '0.1.0';
    File('${catalog.path}/pubspec.yaml').writeAsStringSync('version: 0.2.0\n');
    expect(generate, failsWith('Version mismatch'));
  });

  test('rejects unknown modules, languages and keys', () {
    config['modules'] = ['billing'];
    expect(generate, failsWith('Unknown module'));
    config['modules'] = ['common'];
    config['locales'] = ['fr'];
    expect(generate, failsWith('Unknown locale'));
    config['locales'] = ['en'];
    config['includeKeys'] = ['authLoginButton'];
    expect(generate, failsWith('Unknown included key'));
    config.remove('includeKeys');
    config['excludeKeys'] = ['typo'];
    expect(generate, failsWith('Unknown excluded key'));
  });

  test('rejects duplicate keys across modules', () {
    (index['modules'] as Map)['auth'] = ['commonConfirm'];
    jsonFile('${catalog.path}/catalog/index.json', index);
    expect(generate, failsWith('Duplicate catalog key'));
  });

  test('rejects duplicate and empty selections', () {
    config['locales'] = ['en', 'en'];
    expect(generate, failsWith('duplicates'));
    config['locales'] = ['en'];
    config['includeKeys'] = ['commonDelete'];
    expect(generate, failsWith('no translation keys'));
  });

  test('rejects missing selected translation before mutating prior output', () {
    generate();
    final oldOutput = File(
      '${app.path}/lib/l10n/arb/app_en.arb',
    ).readAsStringSync();
    final path = '${catalog.path}/catalog/chat/app_en.arb';
    final arb = read(path)..remove('chatReadCount');
    jsonFile(path, arb);
    expect(generate, failsWith('Missing translation chatReadCount'));
    expect(
      File('${app.path}/lib/l10n/arb/app_en.arb').readAsStringSync(),
      oldOutput,
    );
  });

  test('rejects override of excluded or misspelled keys', () {
    jsonFile('${app.path}/l10n_overrides/en.json', {'commonDelete': 'Remove'});
    expect(generate, failsWith('unknown or excluded'));
  });

  test('rejects altered message parameters and parameter types', () {
    jsonFile('${app.path}/l10n_overrides/en.json', {
      'chatReadCount': 'Seen by {total}',
    });
    expect(generate, failsWith('Placeholder names mismatch'));
    File('${app.path}/l10n_overrides/en.json').deleteSync();
    final path = '${catalog.path}/catalog/chat/app_en.arb';
    final arb = read(path);
    arb['@chatReadCount']['placeholders']['count']['type'] = 'String';
    jsonFile(path, arb);
    expect(generate, failsWith('Placeholder type mismatch'));
  });

  test('rejects missing default-language parameter metadata', () {
    final path = '${catalog.path}/catalog/chat/app_zh.arb';
    final arb = read(path)..remove('@chatReadCount');
    jsonFile(path, arb);
    expect(generate, failsWith('Placeholder metadata mismatch'));
  });

  test('protects hand-written output files, yaml and nested symlinks', () {
    final userFile = File('${app.path}/lib/l10n/keep.dart')
      ..parent.createSync(recursive: true)
      ..writeAsStringSync('// user source');
    expect(generate, failsWith('not owned'));
    userFile.deleteSync();
    final yaml = File('${app.path}/l10n.yaml')
      ..writeAsStringSync('arb-dir: hand_written\n');
    expect(generate, failsWith('Existing l10n.yaml'));
    yaml.deleteSync();
    generate();
    File('${app.path}/lib/l10n/keep.dart').writeAsStringSync('// user source');
    expect(generate, failsWith('Unowned file'));
    File('${app.path}/lib/l10n/keep.dart').deleteSync();
    Link('${app.path}/lib/l10n/link').createSync(catalog.absolute.path);
    expect(generate, failsWith('Symlink'));
  });

  test('rejects traversal and overlap with hand-written overrides', () {
    config['outputDir'] = 'lib/../../outside';
    expect(generate, failsWith('safe relative path'));
    config['outputDir'] = 'lib/l10n';
    config['overridesDir'] = 'lib/l10n/overrides';
    expect(generate, failsWith('outside outputDir'));
  });

  test('consumer profile preserves its own scope, values and metadata', () {
    config['profile'] = 'sdk';
    config['locales'] = ['zh', 'en'];
    config['templateLocale'] = 'zh';
    config['excludeKeys'] = <String>[];
    jsonFile('${catalog.path}/catalog/profiles/sdk.json', {
      'schemaVersion': 1,
      'locales': ['zh', 'en'],
      'keys': ['chatReadCount', 'commonConfirm'],
      'overrides': {
        'en': {'commonConfirm': 'SDK OK'}
      },
      'metadata': {
        'zh': {
          '@chatReadCount': {
            'placeholders': {
              'count': {'type': 'int'}
            }
          }
        },
        'en': <String, dynamic>{},
      },
    });
    final receipt = generate();
    final en = read('${app.path}/lib/l10n/arb/app_en.arb');
    expect(receipt['keys'], ['chatReadCount', 'commonConfirm']);
    expect(en['commonConfirm'], 'SDK OK');
    expect(en.containsKey('@chatReadCount'), isFalse);
    expect(en.containsKey('chatNewMessages'), isFalse);
  });

  test('flat layout retains established consumer import paths', () {
    config['layout'] = 'flat';
    generate();
    expect(File('${app.path}/lib/l10n/app_en.arb').existsSync(), isTrue);
    expect(Directory('${app.path}/lib/l10n/arb').existsSync(), isFalse);
    expect(File('${app.path}/l10n.yaml').readAsStringSync(),
        contains('output-dir: lib/l10n\n'));
    File('${app.path}/lib/l10n/app_localizations.dart')
        .writeAsStringSync('// Flutter generated');
    generateBundle(packageRoot: catalog, consumerRoot: app, checkOnly: true);
    expect(File('${app.path}/lib/l10n/app_localizations.dart').existsSync(),
        isTrue);
  });

  test('check mode detects stale resources without modifying them', () {
    generate();
    final file = File('${app.path}/lib/l10n/arb/app_en.arb');
    final altered = read(file.path)..['commonConfirm'] = 'Unmanaged edit';
    jsonFile(file.path, altered);
    final bytes = file.readAsBytesSync();
    expect(
        () => generateBundle(
            packageRoot: catalog, consumerRoot: app, checkOnly: true),
        failsWith('stale'));
    expect(file.readAsBytesSync(), bytes);
  });
}
