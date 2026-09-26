class RawMaterialStockLineModel {
  final String productPublicId;
  final String name;
  final String incomingKg;
  final String packedKg;
  final String availableKg;

  const RawMaterialStockLineModel({
    required this.productPublicId,
    this.name = '',
    this.incomingKg = '',
    this.packedKg = '',
    this.availableKg = '',
  });

  factory RawMaterialStockLineModel.fromJson(Map<String, dynamic> json) {
    return RawMaterialStockLineModel(
      productPublicId: '${json['product'] ?? ''}',
      name: json['name'] as String? ?? '',
      incomingKg: _decimalOf(json['incoming_kg']),
      packedKg: _decimalOf(json['packed_kg']),
      availableKg: _decimalOf(json['available_kg']),
    );
  }

  num? get incomingValue => num.tryParse(incomingKg);

  num? get packedValue => num.tryParse(packedKg);

  num? get availableValue => num.tryParse(availableKg);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}

class RawMaterialStockModel {
  final String asOf;
  final List<RawMaterialStockLineModel> lines;

  const RawMaterialStockModel({this.asOf = '', this.lines = const []});

  factory RawMaterialStockModel.fromJson(Map<String, dynamic> json) {
    final dynamic lines = json['lines'];

    return RawMaterialStockModel(
      asOf: '${json['as_of'] ?? ''}',
      lines: lines is List
          ? lines
                .whereType<Map>()
                .map(
                  (line) => RawMaterialStockLineModel.fromJson(
                    Map<String, dynamic>.from(line),
                  ),
                )
                .toList()
          : const [],
    );
  }
}
