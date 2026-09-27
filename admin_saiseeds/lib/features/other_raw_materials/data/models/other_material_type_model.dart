class OtherMaterialUnitType {
  OtherMaterialUnitType._();

  static const String COUNT = 'count';
  static const String KG = 'kg';
  static const String LITRE = 'litre';
}

class OtherMaterialTypeModel {
  final int id;
  final String name;
  final String unitType;

  const OtherMaterialTypeModel({
    required this.id,
    required this.name,
    this.unitType = '',
  });

  factory OtherMaterialTypeModel.fromJson(Map<String, dynamic> json) {
    return OtherMaterialTypeModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      unitType: '${json['unit_type'] ?? ''}',
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
