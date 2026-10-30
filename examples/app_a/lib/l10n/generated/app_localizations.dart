import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppALocalizations
/// returned by `AppALocalizations.of(context)`.
///
/// Applications need to include `AppALocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppALocalizations.localizationsDelegates,
///   supportedLocales: AppALocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppALocalizations.supportedLocales
/// property.
abstract class AppALocalizations {
  AppALocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppALocalizations of(BuildContext context) {
    return Localizations.of<AppALocalizations>(context, AppALocalizations)!;
  }

  static const LocalizationsDelegate<AppALocalizations> delegate =
      _AppALocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('en')];

  /// Email hint
  ///
  /// In en, this message translates to:
  /// **'Enter email address'**
  String get authHintEmail;

  /// Password hint
  ///
  /// In en, this message translates to:
  /// **'Enter password'**
  String get authHintPassword;

  /// Login button
  ///
  /// In en, this message translates to:
  /// **'Sign In'**
  String get authLoginButton;

  /// Login page title
  ///
  /// In en, this message translates to:
  /// **'Sign in to App A'**
  String get authLoginTitle;

  /// Group member count in title
  ///
  /// In en, this message translates to:
  /// **'({count})'**
  String chatGroupMemberCount(int count);

  /// Chat presentation: chatHomeNewMessages
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one {{count} new message} other {{count} new messages}}'**
  String chatHomeNewMessages(int count);

  /// chatInputHint
  ///
  /// In en, this message translates to:
  /// **'Type a message...'**
  String get chatInputHint;

  /// Chat read count
  ///
  /// In en, this message translates to:
  /// **'Read by {count}'**
  String chatReadCount(int count);

  /// Peer recalled message
  ///
  /// In en, this message translates to:
  /// **'{sender} recalled a message'**
  String chatRecalledPeer(String sender);

  /// Reply preview sender
  ///
  /// In en, this message translates to:
  /// **'Reply to {sender}'**
  String chatReplyTo(String sender);

  /// Cancel button
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// Confirm button
  ///
  /// In en, this message translates to:
  /// **'OK'**
  String get commonConfirm;

  /// Delete button
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get commonDelete;

  /// Retry
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get commonRetry;

  /// Save button
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSave;

  /// Send
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get commonSend;

  /// Localized display formatMinutesAgo
  ///
  /// In en, this message translates to:
  /// **'{count, plural, one {{count} minute ago} other {{count} minutes ago}}'**
  String formatMinutesAgo(int count);

  /// Language
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get settingsLanguage;

  /// settingsSignOutDeviceConfirm
  ///
  /// In en, this message translates to:
  /// **'Sign out “{name}”?'**
  String settingsSignOutDeviceConfirm(String name);

  /// Settings title
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;
}

class _AppALocalizationsDelegate
    extends LocalizationsDelegate<AppALocalizations> {
  const _AppALocalizationsDelegate();

  @override
  Future<AppALocalizations> load(Locale locale) {
    return SynchronousFuture<AppALocalizations>(
        lookupAppALocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppALocalizationsDelegate old) => false;
}

AppALocalizations lookupAppALocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppALocalizationsEn();
  }

  throw FlutterError(
      'AppALocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
