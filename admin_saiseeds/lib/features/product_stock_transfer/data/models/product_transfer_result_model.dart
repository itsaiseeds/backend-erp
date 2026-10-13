/// The `source`/`target` side of a transfer response -- just enough to show
/// what the product now holds after the move.
class ProductTransferSide {
  final String publicId;
  final String name;
  final String availableKg;

  const ProductTransferSide({
    this.publicId = '',
    this.name = '',
    this.availableKg = '',
  });

  factory ProductTransferSide.fromJson(Map<String, dynamic> json) {
    return ProductTransferSide(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
      availableKg: _decimalOf(json['available_kg']),
    );
  }

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}

/// Response of `POST /api/sales-admin/transfer-product`.
class ProductTransferResult {
  final String transferredKg;
  final ProductTransferSide source;
  final ProductTransferSide target;

  const ProductTransferResult({
    this.transferredKg = '',
    this.source = const ProductTransferSide(),
    this.target = const ProductTransferSide(),
  });

  factory ProductTransferResult.fromJson(Map<String, dynamic> json) {
    final dynamic source = json['source'];
    final dynamic target = json['target'];

    return ProductTransferResult(
      transferredKg: '${json['transferred_kg'] ?? ''}',
      source: source is Map
          ? ProductTransferSide.fromJson(Map<String, dynamic>.from(source))
          : const ProductTransferSide(),
      target: target is Map
          ? ProductTransferSide.fromJson(Map<String, dynamic>.from(target))
          : const ProductTransferSide(),
    );
  }
}
