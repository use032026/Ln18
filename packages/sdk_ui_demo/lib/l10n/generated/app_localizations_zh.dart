// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class SdkLocalizationsZh extends SdkLocalizations {
  SdkLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String chatGroupMemberCount(int count) {
    return '($count)';
  }

  @override
  String chatHomeNewMessages(int count) {
    return '有 $count 条新消息';
  }

  @override
  String get chatInputHint => '输入消息...';

  @override
  String chatReadCount(int count) {
    return '已读 $count 人';
  }

  @override
  String chatRecalledPeer(String sender) {
    return '$sender撤回了一条消息';
  }

  @override
  String chatReplyTo(String sender) {
    return '回复 $sender';
  }

  @override
  String get commonCancel => '取消';

  @override
  String get commonConfirm => '确定';

  @override
  String get commonRetry => '重试';

  @override
  String get commonSave => '保存';

  @override
  String get commonSend => '发送消息';

  @override
  String formatMinutesAgo(int count) {
    return '$count分钟前';
  }

  @override
  String get settingsLanguage => '系统语言';

  @override
  String settingsSignOutDeviceConfirm(String name) {
    return '确定要让“$name”退出登录吗？';
  }

  @override
  String get settingsTitle => '设置';
}
