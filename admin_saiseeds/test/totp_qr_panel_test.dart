import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/utils/share/phone_number_formatter.dart';
import 'package:admin_saiseeds/core/utils/share/totp_message_builder.dart';
import 'package:admin_saiseeds/core/widgets/buttons/secondary_button.dart';
import 'package:admin_saiseeds/core/widgets/feedback/totp_qr_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';

const String _uri =
    'otpauth://totp/Saiseeds:test@example.com?secret=ABCD&issuer=Saiseeds';

Future<void> _pumpPanel(
  WidgetTester tester, {
  String provisioningUri = _uri,
  String phoneNumber = '9876543210',
  String subjectName = 'Sales Person User',
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1000, 1200);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: TotpQrPanel(
            provisioningUri: provisioningUri,
            phoneNumber: phoneNumber,
            subjectName: subjectName,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

SecondaryButton _buttonNamed(WidgetTester tester, String label) {
  return tester.widget<SecondaryButton>(
    find.ancestor(of: find.text(label), matching: find.byType(SecondaryButton)),
  );
}

void main() {
  group('whatsapp number formatting', () {
    test('a ten digit local number gains the India dial code', () {
      expect(
        PhoneNumberFormatter.toWhatsAppNumber('9876543210'),
        '919876543210',
      );
    });

    test('punctuation and spaces are stripped', () {
      expect(
        PhoneNumberFormatter.toWhatsAppNumber('+91 98765-43210'),
        '919876543210',
      );
      expect(
        PhoneNumberFormatter.toWhatsAppNumber('(987) 654 3210'),
        '919876543210',
      );
    });

    test('a leading zero is dropped before the dial code is added', () {
      expect(
        PhoneNumberFormatter.toWhatsAppNumber('09876543210'),
        '919876543210',
      );
    });

    test('a number that already carries a country code is left alone', () {
      expect(
        PhoneNumberFormatter.toWhatsAppNumber('919876543210'),
        '919876543210',
      );
    });

    test('an empty or non-numeric value is not dialable', () {
      expect(PhoneNumberFormatter.toWhatsAppNumber(''), '');
      expect(PhoneNumberFormatter.toWhatsAppNumber('   '), '');
      expect(PhoneNumberFormatter.toWhatsAppNumber('n/a'), '');
      expect(PhoneNumberFormatter.isDialable(''), isFalse);
      // An all-zero placeholder is not a real number, so it is not dialable.
      expect(PhoneNumberFormatter.isDialable('0000000000'), isFalse);
    });
  });

  group('the welcome message', () {
    String messageFor(String name) => TotpMessageBuilder.build(name: name);

    test('greets the person by name', () {
      expect(messageFor('Hitesh Mori'), startsWith('Hello Hitesh Mori,'));
    });

    test('a nameless record still greets cleanly', () {
      final String message = messageFor('   ');

      expect(message, startsWith('Hello,'));
      expect(message, isNot(contains('Hello ,')));
    });

    test('it welcomes and explains what to do', () {
      final String message = messageFor('Hitesh Mori');

      expect(message, contains(AppStrings.TOTP_WHATSAPP_INTRO));
      expect(message, contains(AppStrings.TOTP_WHATSAPP_STEPS));
      expect(message, contains(AppStrings.TOTP_WHATSAPP_CLOSING));
    });

    test('the secret never appears in the message text', () {
      final String message = messageFor('Hitesh Mori');

      // The QR image carries the secret; putting it in plain text as well
      // would leak it to anyone who forwards the chat.
      expect(message, isNot(contains(_uri)));
      expect(message, isNot(contains('otpauth')));
      expect(message, isNot(contains('secret')));
    });
  });

  group('the QR panel', () {
    testWidgets('renders the code with both actions', (tester) async {
      await _pumpPanel(tester);

      expect(find.byType(QrImageView), findsOneWidget);
      expect(find.text(AppStrings.TOTP_SEND_WHATSAPP), findsOneWidget);
      expect(find.text(AppStrings.TOTP_DOWNLOAD_QR), findsOneWidget);
    });

    testWidgets('the QR sits in a boundary so it can be exported', (
      tester,
    ) async {
      await _pumpPanel(tester);

      expect(
        find.ancestor(
          of: find.byType(QrImageView),
          matching: find.byType(RepaintBoundary),
        ),
        findsWidgets,
      );
    });

    testWidgets('with no phone on record WhatsApp is disabled', (tester) async {
      await _pumpPanel(tester, phoneNumber: '');

      expect(
        _buttonNamed(tester, AppStrings.TOTP_SEND_WHATSAPP).onPressed,
        isNull,
      );
      expect(find.text(AppStrings.TOTP_NO_PHONE), findsOneWidget);
    });

    testWidgets('download stays available without a phone number', (
      tester,
    ) async {
      await _pumpPanel(tester, phoneNumber: '');

      expect(
        _buttonNamed(tester, AppStrings.TOTP_DOWNLOAD_QR).onPressed,
        isNotNull,
      );
    });

    testWidgets('with a phone on record WhatsApp is enabled', (tester) async {
      await _pumpPanel(tester);

      expect(
        _buttonNamed(tester, AppStrings.TOTP_SEND_WHATSAPP).onPressed,
        isNotNull,
      );
      expect(find.text(AppStrings.TOTP_NO_PHONE), findsNothing);
    });

    testWidgets('an account with no TOTP shows neither code nor actions', (
      tester,
    ) async {
      await _pumpPanel(tester, provisioningUri: '');

      expect(find.byType(QrImageView), findsNothing);
      expect(find.text(AppStrings.TOTP_SEND_WHATSAPP), findsNothing);
      expect(find.text(AppStrings.TOTP_DOWNLOAD_QR), findsNothing);
      expect(find.text(AppStrings.TOTP_UNAVAILABLE), findsOneWidget);
    });
  });
}
