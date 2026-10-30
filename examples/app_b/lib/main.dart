import 'package:flutter/material.dart';
import 'package:sdk_ui_demo/sdk_ui_demo.dart';

void main() => runApp(const AppB());

/// The host passes a locale and never registers the SDK's delegate itself.
class AppB extends StatefulWidget {
  const AppB({super.key});

  @override
  State<AppB> createState() => _AppBState();
}

class _AppBState extends State<AppB> {
  Locale _locale = const Locale('en');

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'App B SDK host demo',
    theme: ThemeData(useMaterial3: true),
    home: Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'App B · Host controls',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  ChoiceChip(
                    key: const ValueKey('host-locale-en'),
                    label: const Text('English'),
                    selected: _locale.languageCode == 'en',
                    onSelected: (_) =>
                        setState(() => _locale = const Locale('en')),
                  ),
                  const SizedBox(width: 8),
                  ChoiceChip(
                    key: const ValueKey('host-locale-zh'),
                    label: const Text('简体中文'),
                    selected: _locale.languageCode == 'zh',
                    onSelected: (_) =>
                        setState(() => _locale = const Locale('zh')),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(child: SdkUiDemo(locale: _locale)),
          ],
        ),
      ),
    ),
  );
}
