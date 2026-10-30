import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:im_l10n_app_b/main.dart';

void main() {
  testWidgets('host changes SDK locale without registering its delegate', (
    tester,
  ) async {
    await tester.pumpWidget(const AppB());
    await tester.pumpAndSettle();
    expect(find.text('Send message'), findsOneWidget);
    expect(find.text('Read by 3'), findsOneWidget);
    expect(find.text('3 new messages'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('host-locale-zh')));
    await tester.pumpAndSettle();
    expect(find.text('发送消息'), findsOneWidget);
    expect(find.text('Send message'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('host-locale-en')));
    await tester.pumpAndSettle();
    expect(find.text('Send message'), findsOneWidget);
    expect(find.text('发送消息'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
