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

  /// Bag price for [packets] packets of [packetWeight] kg each.
  ///
  /// [productSellingPrice] is a rate per kilogram (see
  /// Product.price_for_weight), so the total is rate x weight x count. Leaving
  /// the weight out under-prices every sub-kilo packet and over-prices the
  /// rest.
  String? nextValue({
    required num? productSellingPrice,
    required String packetWeight,
    required String packets,
  }) {
    if (_isManuallyEdited) return null;

    final int? packetCount = int.tryParse(packets.trim());
    final num? weight = num.tryParse(packetWeight.trim());

    if (productSellingPrice == null ||
        packetCount == null ||
        packetCount <= 0 ||
        weight == null ||
        weight <= 0) {
      return null;
    }

    final String computed = (productSellingPrice * weight * packetCount)
        .toStringAsFixed(PRICE_DECIMALS);
    _lastAutofilledValue = computed;
    return computed;
  }
}
