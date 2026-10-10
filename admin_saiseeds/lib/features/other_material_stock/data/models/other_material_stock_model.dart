import '../../../other_raw_materials/data/models/other_material_type_model.dart';

/// The product + packet weight a configuration-grouped line is keyed on.
/// Absent when the API answered without ``?group_by=configuration``.
class OtherMaterialStockProductModel {
  final String publicId;
  final String name;

  const OtherMaterialStockProductModel({this.publicId = '', this.name = ''});

  factory OtherMaterialStockProductModel.fromJson(Map<String, dynamic> json) {
    return OtherMaterialStockProductModel(
      publicId: '${json['public_id'] ?? ''}',
      name: '${json['name'] ?? ''}',
    );
  }
}

class OtherMaterialStockLineModel {
  final OtherMaterialTypeModel? materialType;
  final String onHand;
  final OtherMaterialStockProductModel? product;
  final String packetWeight;

  const OtherMaterialStockLineModel({
    this.materialType,
    this.onHand = '',
    this.product,
    this.packetWeight = '',
  });

  factory OtherMaterialStockLineModel.fromJson(Map<String, dynamic> json) {
    final dynamic materialType = json['material_type'];
    final dynamic product = json['product'];

    return OtherMaterialStockLineModel(
      materialType: materialType is Map
          ? OtherMaterialTypeModel.fromJson(
              Map<String, dynamic>.from(materialType),
            )
          : null,
      onHand: _decimalOf(json['on_hand']),
      product: product is Map
          ? OtherMaterialStockProductModel.fromJson(
              Map<String, dynamic>.from(product),
            )
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
    );
  }

  int? get materialTypeId => materialType?.id;

  String get materialTypeName => materialType?.name ?? '';

  String get unitType => materialType?.unitType ?? '';

  num? get onHandValue => num.tryParse(onHand);

  String get productName => product?.name ?? '';

  num? get packetWeightValue => num.tryParse(packetWeight);

  /// "SAI-30 — 1.5 kg" -- blank when the row carries no packaging (the
  /// API answered without ``?group_by=configuration``).
  String get configurationLabel {
    if (productName.isEmpty) return '';
    final num? weight = packetWeightValue;
    if (weight == null) return productName;
    return '$productName — ${_trimWeight(weight)} kg';
  }

  static String _trimWeight(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}

class OtherMaterialStockModel {
  final String asOf;
  final List<OtherMaterialStockLineModel> lines;

  const OtherMaterialStockModel({this.asOf = '', this.lines = const []});

  factory OtherMaterialStockModel.fromJson(Map<String, dynamic> json) {
    final dynamic lines = json['lines'];

    return OtherMaterialStockModel(
      asOf: '${json['as_of'] ?? ''}',
      lines: lines is List
          ? lines
                .whereType<Map>()
                .map(
                  (line) => OtherMaterialStockLineModel.fromJson(
                    Map<String, dynamic>.from(line),
                  ),
                )
                .toList()
          : const [],
    );
  }
}
