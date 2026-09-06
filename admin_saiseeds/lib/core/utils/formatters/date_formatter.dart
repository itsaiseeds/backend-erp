import 'package:intl/intl.dart';
import '../../constants/app_strings.dart';

class DateFormatter {
  DateFormatter._();

  static final DateFormat _display = DateFormat('d MMM yyyy, h:mm a');

  static String label(String? isoValue) {
    final String raw = (isoValue ?? '').trim();
    if (raw.isEmpty) return AppStrings.TABLE_VALUE_UNAVAILABLE;

    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed == null) return AppStrings.TABLE_VALUE_UNAVAILABLE;

    return _display.format(parsed.toLocal());
  }
}
