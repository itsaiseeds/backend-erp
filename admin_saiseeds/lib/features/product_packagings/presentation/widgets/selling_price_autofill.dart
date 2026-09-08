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

  String? nextValue({required num? productSellingPrice, required String packets}) {
    if (_isManuallyEdited) return null;

    final int? packetCount = int.tryParse(packets.trim());
    if (productSellingPrice == null || packetCount == null || packetCount <= 0) {
      return null;
    }

    final String computed = (productSellingPrice * packetCount).toStringAsFixed(
      PRICE_DECIMALS,
    );
    _lastAutofilledValue = computed;
    return computed;
  }
}
