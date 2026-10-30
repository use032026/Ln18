// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class SdkLocalizationsEn extends SdkLocalizations {
  SdkLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String chatGroupMemberCount(int count) {
    return '($count)';
  }

  @override
  String chatHomeNewMessages(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count new messages',
      one: '$count new message',
    );
    return '$_temp0';
  }

  @override
  String get chatInputHint => 'Type a message...';

  @override
  String chatReadCount(int count) {
    return 'Read by $count';
  }

  @override
  String chatRecalledPeer(String sender) {
    return '$sender recalled a message';
  }

  @override
  String chatReplyTo(String sender) {
    return 'Reply to $sender';
  }

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonConfirm => 'OK';

  @override
  String get commonRetry => 'Retry';

  @override
  String get commonSave => 'Save';

  @override
  String get commonSend => 'Send message';

  @override
  String formatMinutesAgo(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count minutes ago',
      one: '$count minute ago',
    );
    return '$_temp0';
  }

  @override
  String get settingsLanguage => 'Language';

  @override
  String settingsSignOutDeviceConfirm(String name) {
    return 'Sign out “$name”?';
  }

  @override
  String get settingsTitle => 'Settings';
}
