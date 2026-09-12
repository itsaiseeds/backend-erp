import '../../constants/app_strings.dart';

class FormValidators {
  FormValidators._();

  static const int PHONE_NUMBER_LENGTH = 10;

  static const int MINIMUM_COUNT = 1;

  static final RegExp _emailPattern = RegExp(r'^[\w.+-]+@[\w-]+\.[\w.-]+$');

  static final RegExp _digitsOnly = RegExp(r'^[0-9]+$');

  static String? requiredField(String? value) {
    return (value ?? '').trim().isEmpty
        ? AppStrings.VALIDATION_NAME_REQUIRED
        : null;
  }

  static String? phoneNumber(String? value) {
    final String raw = (value ?? '').trim();
    if (raw.isEmpty) return AppStrings.VALIDATION_PHONE_REQUIRED;
    if (raw.length != PHONE_NUMBER_LENGTH || !_digitsOnly.hasMatch(raw)) {
      return AppStrings.VALIDATION_PHONE_INVALID;
    }
    return null;
  }

  static String? nonNegativeAmount(String? value) {
    final String raw = (value ?? '').trim();
    if (raw.isEmpty) return AppStrings.VALIDATION_PRICE_REQUIRED;
    final num? parsed = num.tryParse(raw);
    if (parsed == null || parsed < 0) {
      return AppStrings.VALIDATION_PRICE_INVALID;
    }
    return null;
  }

  static String? positiveAmount(String? value) {
    final String raw = (value ?? '').trim();
    if (raw.isEmpty) return AppStrings.VALIDATION_POSITIVE_AMOUNT_REQUIRED;
    final num? parsed = num.tryParse(raw);
    if (parsed == null || parsed <= 0) {
      return AppStrings.VALIDATION_POSITIVE_AMOUNT_INVALID;
    }
    return null;
  }

  static String? positiveCount(String? value) {
    final String raw = (value ?? '').trim();
    if (raw.isEmpty) return AppStrings.VALIDATION_POSITIVE_AMOUNT_REQUIRED;
    if (!_digitsOnly.hasMatch(raw)) return AppStrings.VALIDATION_COUNT_INVALID;
    final int? parsed = int.tryParse(raw);
    if (parsed == null || parsed < MINIMUM_COUNT) {
      return AppStrings.VALIDATION_COUNT_INVALID;
    }
    return null;
  }

  static String? optionalEmail(String? value) {
    final String raw = (value ?? '').trim();
    if (raw.isEmpty) return null;
    return _emailPattern.hasMatch(raw)
        ? null
        : AppStrings.VALIDATION_EMAIL_INVALID;
  }
}
