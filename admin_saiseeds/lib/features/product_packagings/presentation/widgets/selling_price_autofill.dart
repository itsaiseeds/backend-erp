class SellingPriceAutofill {
  bool _isManuallyEdited = false;
  String _lastAutofilledValue = '';

  static const int PRICE_DECIMALS = 2;

  bool get isManuallyEdited => _isManuallyEdited;

  void markManuallyEdited() => _isManuallyEdited = true;

  void adoptExistingValue(String value) {
    if (value.trim().isEmpty) return;
    _isManuallyEdited = true;
  }

  void registerFieldChange(String value) {
    if (value == _lastAutofilledValue) return;
    _isManuallyEdited = true;
  }

  String? nextValue({required num? productSellingPrice, required String bags}) {
    if (_isManuallyEdited) return null;

    final int? bagCount = int.tryParse(bags.trim());
    if (productSellingPrice == null || bagCount == null || bagCount <= 0) {
      return null;
    }

    final String computed = (productSellingPrice * bagCount).toStringAsFixed(
      PRICE_DECIMALS,
    );
    _lastAutofilledValue = computed;
    return computed;
  }
}
