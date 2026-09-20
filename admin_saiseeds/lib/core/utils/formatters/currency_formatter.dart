import 'package:intl/intl.dart';

class CurrencyFormatter {
  CurrencyFormatter._();

  static const String RUPEE_SYMBOL = '\u20B9';

  static final NumberFormat _whole = NumberFormat('#,##,##0', 'en_IN');
  static final NumberFormat _withPaise = NumberFormat('#,##,##0.00', 'en_IN');

  static String rupees(num value) {
    final String amount = value == value.roundToDouble()
        ? _whole.format(value)
        : _withPaise.format(value);
    return '$RUPEE_SYMBOL$amount';
  }
}
