import '../../constants/app_strings.dart';

class TotpMessageBuilder {
  TotpMessageBuilder._();

  static String greetingFor(String name) {
    final String trimmed = name.trim();
    if (trimmed.isEmpty) return '${AppStrings.TOTP_WHATSAPP_GREETING},';
    return '${AppStrings.TOTP_WHATSAPP_GREETING} $trimmed,';
  }

  static String build({required String name}) {
    return [
      greetingFor(name),
      '',
      AppStrings.TOTP_WHATSAPP_INTRO,
      '',
      AppStrings.TOTP_WHATSAPP_STEPS,
      '',
      AppStrings.TOTP_WHATSAPP_CLOSING,
    ].join('\n');
  }
}
