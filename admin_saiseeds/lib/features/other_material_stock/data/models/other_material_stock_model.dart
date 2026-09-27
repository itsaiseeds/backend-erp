import '../../../other_raw_materials/data/models/other_material_type_model.dart';

class OtherMaterialStockLineModel {
  final OtherMaterialTypeModel? materialType;
  final String onHand;

  const OtherMaterialStockLineModel({this.materialType, this.onHand = ''});

  factory OtherMaterialStockLineModel.fromJson(Map<String, dynamic> json) {
    final dynamic materialType = json['material_type'];

    return OtherMaterialStockLineModel(
      materialType: materialType is Map
          ? OtherMaterialTypeModel.fromJson(
              Map<String, dynamic>.from(materialType),
            )
          : null,
      onHand: _decimalOf(json['on_hand']),
    );
  }

  int? get materialTypeId => materialType?.id;

  String get materialTypeName => materialType?.name ?? '';

  String get unitType => materialType?.unitType ?? '';

  num? get onHandValue => num.tryParse(onHand);

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
