/// One recently-dispatched lot, tagged with the product it was used for --
/// the API returns this list across every product (``limit`` lots *per*
/// product), so a picker for one product's line must filter down to its own
/// [productName] before showing options.
class DispatchLotNumberModel {
  final String lotNumber;
  final int productId;
  final String productName;
  final String lastUsedAt;

  const DispatchLotNumberModel({
    required this.lotNumber,
    this.productId = 0,
    this.productName = '',
    this.lastUsedAt = '',
  });

  factory DispatchLotNumberModel.fromJson(Map<String, dynamic> json) {
    return DispatchLotNumberModel(
      lotNumber: '${json['lot_number'] ?? ''}',
      productId: _intOf(json['product_id']),
      productName: '${json['product_name'] ?? ''}',
      lastUsedAt: _textOf(json['last_used_at']),
    );
  }

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }

  static int _intOf(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
