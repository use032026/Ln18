import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:im_l10n_app_a/l10n/generated/app_localizations.dart';
import 'package:im_l10n_app_a/main.dart';

void main() {
  test('A includes English only and preserves typed plural messages', () async {
    expect(AppALocalizations.supportedLocales, const [Locale('en')]);
    final text = await AppALocalizations.delegate.load(const Locale('en'));
    expect(text.authLoginTitle, 'Sign in to App A');
    expect(text.commonSend, 'Send');
    expect(text.chatReadCount(3), 'Read by 3');
    expect(text.chatRecalledPeer('Alex'), 'Alex recalled a message');
    expect(text.chatHomeNewMessages(1), '1 new message');
    expect(text.chatHomeNewMessages(3), '3 new messages');
    expect(text.formatMinutesAgo(1), '1 minute ago');
    expect(text.formatMinutesAgo(5), '5 minutes ago');
  });

  testWidgets('A renders its override and real catalog messages', (
    tester,
  ) async {
    await tester.pumpWidget(const AppA());
    await tester.pumpAndSettle();
    expect(find.text('Sign in to App A'), findsOneWidget);
    expect(find.text('Read by 3'), findsOneWidget);
    expect(find.text('1 new message'), findsOneWidget);
    expect(find.text('3 new messages'), findsOneWidget);
    expect(find.text('5 minutes ago'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
