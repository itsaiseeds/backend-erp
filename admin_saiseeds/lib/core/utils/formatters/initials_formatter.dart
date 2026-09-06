class InitialsFormatter {
  InitialsFormatter._();

  static const String _fallback = 'S';
  static const int _maxInitials = 2;

  static String fromName(String? name) {
    final parts = (name ?? '')
        .trim()
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty)
        .toList();

    if (parts.isEmpty) return _fallback;

    final buffer = StringBuffer();
    for (final part in parts.take(_maxInitials)) {
      buffer.write(part[0].toUpperCase());
    }
    return buffer.toString();
  }
}
