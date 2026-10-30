import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sdk_ui_demo/l10n/generated/app_localizations.dart';
import 'package:sdk_ui_demo/sdk_ui_demo.dart';

void main() {
  test('SDK has its own English and Chinese translations', () async {
    expect(
      SdkLocalizations.supportedLocales,
      containsAll(const [Locale('en'), Locale('zh')]),
    );
    final english = await SdkLocalizations.delegate.load(const Locale('en'));
    final chinese = await SdkLocalizations.delegate.load(const Locale('zh'));
    expect(english.commonSend, 'Send message');
    expect(chinese.commonSend, '发送消息');
    expect(english.chatHomeNewMessages(1), '1 new message');
    expect(english.chatHomeNewMessages(3), '3 new messages');
    expect(english.formatMinutesAgo(5), '5 minutes ago');
    expect(chinese.chatReadCount(3), contains('3'));
    expect(chinese.chatRecalledPeer('Alex'), contains('Alex'));
    expect(
      chinese.settingsSignOutDeviceConfirm('Demo device'),
      contains('Demo device'),
    );
  });

  testWidgets('SDK owns delegate registration and reacts to host locale', (
    tester,
  ) async {
    await tester.pumpWidget(const SdkUiDemo());
    await tester.pumpAndSettle();
    expect(find.text('Send message'), findsOneWidget);
    expect(find.text('Read by 3'), findsOneWidget);
    await tester.pumpWidget(const SdkUiDemo(locale: Locale('zh')));
    await tester.pumpAndSettle();
    expect(find.text('发送消息'), findsOneWidget);
    expect(find.text('Send message'), findsNothing);
    final chinese = await SdkLocalizations.delegate.load(const Locale('zh'));
    expect(find.text(chinese.chatReadCount(3)), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
