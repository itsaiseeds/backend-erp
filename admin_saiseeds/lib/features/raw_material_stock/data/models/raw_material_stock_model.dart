class RawMaterialStockLineModel {
  final String productPublicId;
  final String name;
  final String incomingKg;
  final String packedKg;
  final String wastedKg;
  final String rejectedKg;
  final String availableKg;

  /// Wasted kilograms already spoken for by a CONFIRMED waste order, not yet
  /// dispatched.
  final String wasteReservedKg;

  /// Wasted kilograms that already left on a DISPATCHED/DELIVERED waste
  /// order.
  final String wasteConsumedKg;

  /// What is left of [wastedKg] after [wasteReservedKg] and [wasteConsumedKg]
  /// -- the kilograms still free to put on a new waste order.
  final String wasteAvailableKg;

  const RawMaterialStockLineModel({
    required this.productPublicId,
    this.name = '',
    this.incomingKg = '',
    this.packedKg = '',
    this.wastedKg = '',
    this.rejectedKg = '',
    this.availableKg = '',
    this.wasteReservedKg = '',
    this.wasteConsumedKg = '',
    this.wasteAvailableKg = '',
  });

  factory RawMaterialStockLineModel.fromJson(Map<String, dynamic> json) {
    return RawMaterialStockLineModel(
      productPublicId: '${json['product'] ?? ''}',
      name: json['name'] as String? ?? '',
      incomingKg: _decimalOf(json['incoming_kg']),
      packedKg: _decimalOf(json['packed_kg']),
      wastedKg: _decimalOf(json['wasted_kg']),
      rejectedKg: _decimalOf(json['rejected_kg']),
      availableKg: _decimalOf(json['available_kg']),
      wasteReservedKg: _decimalOf(json['waste_reserved_kg']),
      wasteConsumedKg: _decimalOf(json['waste_consumed_kg']),
      wasteAvailableKg: _decimalOf(json['waste_available_kg']),
    );
  }

  num? get incomingValue => num.tryParse(incomingKg);

  num? get packedValue => num.tryParse(packedKg);

  num? get wastedValue => num.tryParse(wastedKg);

  num? get rejectedValue => num.tryParse(rejectedKg);

  num? get availableValue => num.tryParse(availableKg);

  num? get wasteReservedValue => num.tryParse(wasteReservedKg);

  num? get wasteConsumedValue => num.tryParse(wasteConsumedKg);

  num? get wasteAvailableValue => num.tryParse(wasteAvailableKg);

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
