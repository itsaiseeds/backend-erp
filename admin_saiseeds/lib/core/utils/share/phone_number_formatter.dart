class PhoneNumberFormatter {
  PhoneNumberFormatter._();

  static const String INDIA_DIAL_CODE = '91';
  static const int LOCAL_NUMBER_LENGTH = 10;

  static String digitsOf(String value) =>
      value.replaceAll(RegExp(r'[^0-9]'), '');

  static String toWhatsAppNumber(String value) {
    String digits = digitsOf(value);
    if (digits.isEmpty) return '';

    while (digits.startsWith('0')) {
      digits = digits.substring(1);
    }
    if (digits.isEmpty) return '';

    if (digits.length == LOCAL_NUMBER_LENGTH) {
      return '$INDIA_DIAL_CODE$digits';
    }
    return digits;
  }

  static bool isDialable(String value) => toWhatsAppNumber(value).isNotEmpty;
}
