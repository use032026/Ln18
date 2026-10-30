library;

import 'package:flutter/material.dart';

import 'l10n/generated/app_localizations.dart';

/// A lightweight SDK UI with an independent localization scope.
///
/// Its host selects the locale. The SDK owns delegate registration and uses
/// only its generated subset; the catalog is a development dependency only.
class SdkUiDemo extends StatelessWidget {
  const SdkUiDemo({super.key, this.locale = const Locale('en')});

  final Locale locale;

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'SDK translation demo',
    locale: locale,
    localizationsDelegates: SdkLocalizations.localizationsDelegates,
    supportedLocales: SdkLocalizations.supportedLocales,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff176d57)),
    ),
    home: const _SdkPanel(),
  );
}

class _SdkPanel extends StatelessWidget {
  const _SdkPanel();

  @override
  Widget build(BuildContext context) {
    final text = SdkLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Embedded SDK · Translation demo')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'DEMO · en / zh · 3 modules · 15 keys per locale',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Sample values demonstrate SDK-owned text only. '
                  'No network request or messaging action is performed.',
                ),
                const SizedBox(height: 20),
                _PhraseCard(
                  label: 'chat · shared messages',
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
                  label: 'common · SDK override',
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final phrase in [
                        text.commonConfirm,
                        text.commonCancel,
                        text.commonSave,
                        text.commonSend,
                        text.commonRetry,
                      ])
                        Chip(label: Text(phrase)),
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
