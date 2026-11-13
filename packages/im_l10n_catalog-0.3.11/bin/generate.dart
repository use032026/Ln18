import 'dart:io';
import 'dart:isolate';

import 'package:im_l10n_catalog/im_l10n_catalog.dart';

Future<void> main(List<String> args) async {
  final checkOnly = args.contains('--check');
  final positional = args.where((arg) => arg != '--check').toList();
  if (positional.length > 1 || args.contains('--help')) {
    stdout.writeln(
      'Usage: dart run im_l10n_catalog:generate [l10n.bundle.json] [--check]',
    );
    exitCode = args.contains('--help') ? 0 : 64;
    return;
  }
  try {
    final anchor = await Isolate.resolvePackageUri(
      Uri.parse('package:im_l10n_catalog/src/package_anchor.dart'),
    );
    if (anchor == null) {
      throw const CatalogException('Cannot locate im_l10n_catalog package.');
    }
    final packageRoot = File.fromUri(anchor).parent.parent.parent;
    final receipt = generateBundle(
      packageRoot: packageRoot,
      consumerRoot: Directory.current,
      configPath: positional.isEmpty ? 'l10n.bundle.json' : positional.single,
      checkOnly: checkOnly,
    );
    stdout.writeln(
      '${checkOnly ? 'Verified' : 'Generated'} ${(receipt['keys'] as List).length} keys for '
      '${(receipt['locales'] as List).join(', ')} from '
      'im_l10n_catalog ${receipt['catalogVersion']}.',
    );
    if (!checkOnly) stdout.writeln('Next: flutter gen-l10n');
  } on CatalogException catch (error) {
    stderr.writeln('Translation bundle error: ${error.message}');
    exitCode = 1;
  } on FileSystemException catch (error) {
    stderr.writeln('Translation bundle file error: ${error.message}');
    exitCode = 1;
  }
}
