import 'package:flutter/material.dart';

import 'l10n/generated/app_localizations.dart';

void main() => runApp(const AppA());

/// A client that includes all four example modules, in English only.
class AppA extends StatelessWidget {
  const AppA({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'App A translation demo',
    locale: const Locale('en'),
    localizationsDelegates: AppALocalizations.localizationsDelegates,
    supportedLocales: AppALocalizations.supportedLocales,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff3156a3)),
    ),
    home: const _ClientDemo(),
  );
}

class _ClientDemo extends StatelessWidget {
  const _ClientDemo();

  @override
  Widget build(BuildContext context) {
    final text = AppALocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('A · Client translation demo')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'DEMO · English only · 4 modules · 20 keys',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Sample data below demonstrates translations only. '
                  'No account, messaging, or device action is performed.',
                ),
                const SizedBox(height: 20),
                _PhraseCard(
                  label: 'auth · App A override',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        text.authLoginTitle,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 12),
                      Text(text.authHintEmail),
                      const SizedBox(height: 8),
                      Text(text.authHintPassword),
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: null,
                        child: Text(text.authLoginButton),
                      ),
                    ],
                  ),
                ),
                _PhraseCard(
                  label: 'chat · parameters and plurals',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(text.chatInputHint),
                      Text(text.chatReadCount(3)),
                      Text(text.chatRecalledPeer('Alex')),
                      Text(text.chatReplyTo('Alex')),
                      Text(text.chatGroupMemberCount(12)),
                      const Divider(),
                      Text(text.chatHomeNewMessages(1)),
                      Text(text.chatHomeNewMessages(3)),
                      Text(text.formatMinutesAgo(1)),
                      Text(text.formatMinutesAgo(5)),
                    ],
                  ),
                ),
                _PhraseCard(
                  label: 'settings',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        text.settingsTitle,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      Text(text.settingsLanguage),
                      Text(text.settingsSignOutDeviceConfirm('Demo device')),
                    ],
                  ),
                ),
                _PhraseCard(
                  label: 'common',
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final phrase in [
                        text.commonConfirm,
                        text.commonCancel,
                        text.commonSave,
                        text.commonDelete,
                        text.commonSend,
                        text.commonRetry,
                      ])
                        Chip(label: Text(phrase)),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PhraseCard extends StatelessWidget {
  const _PhraseCard({required this.label, required this.child});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 16),
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 12),
          child,
        ],
      ),
    ),
  );
}
