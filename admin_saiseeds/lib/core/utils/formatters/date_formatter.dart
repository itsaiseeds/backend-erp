import 'package:intl/intl.dart';
import '../../constants/app_strings.dart';

class DateFormatter {
  DateFormatter._();

  static const Duration IST_OFFSET = Duration(hours: 5, minutes: 30);

  static final DateFormat _display = DateFormat('d MMM yyyy, h:mm a');
  static final DateFormat _dayOnly = DateFormat('d MMM yyyy');

  static String label(String? isoValue) {
    final String raw = (isoValue ?? '').trim();
    if (raw.isEmpty) return AppStrings.TABLE_VALUE_UNAVAILABLE;

    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed == null) return AppStrings.TABLE_VALUE_UNAVAILABLE;

    return '${_display.format(parsed.toUtc().add(IST_OFFSET))} '
        '${AppStrings.TIMEZONE_IST}';
  }

  static String dayLabel(DateTime? value) {
    if (value == null) return AppStrings.TABLE_VALUE_UNAVAILABLE;
    return _dayOnly.format(value);
  }

  static String instantLabel(DateTime? value) {
    if (value == null) return AppStrings.TABLE_VALUE_UNAVAILABLE;
    return '${_display.format(value.toUtc().add(IST_OFFSET))} '
        '${AppStrings.TIMEZONE_IST}';
  }
}
