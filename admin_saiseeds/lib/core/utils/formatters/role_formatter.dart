import '../../constants/app_strings.dart';

class RoleFormatter {
  RoleFormatter._();

  static String label(String? role) {
    final raw = (role ?? '').trim();
    if (raw.isEmpty) return AppStrings.PROFILE_ROLE_UNKNOWN;

    final words = raw
        .replaceAll(RegExp(r'[_\-]+'), ' ')
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .map((word) => word[0].toUpperCase() + word.substring(1).toLowerCase());

    return words.join(' ');
  }
}
