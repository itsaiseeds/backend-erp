import 'other_material_type_model.dart';

class RecipeProductRef {
  final String publicId;
  final String name;

  const RecipeProductRef({required this.publicId, required this.name});

  factory RecipeProductRef.fromJson(Map<String, dynamic> json) {
    return RecipeProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class OtherMaterialRecipeModel {
  final String publicId;
  final RecipeProductRef? product;
  final OtherMaterialTypeModel? materialType;
  final String packetWeight;
  final String quantity;

  const OtherMaterialRecipeModel({
    required this.publicId,
    this.product,
    this.materialType,
    this.packetWeight = '',
    this.quantity = '',
  });

  factory OtherMaterialRecipeModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final dynamic materialType = json['material_type'];

    return OtherMaterialRecipeModel(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? RecipeProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      materialType: materialType is Map
          ? OtherMaterialTypeModel.fromJson(
              Map<String, dynamic>.from(materialType),
            )
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
      quantity: _decimalOf(json['quantity']),
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  String get materialTypeName => materialType?.name ?? '';

  int? get materialTypeId => materialType?.id;

  String get unitType => materialType?.unitType ?? '';

  num? get packetWeightValue => num.tryParse(packetWeight);

  num? get quantityValue => num.tryParse(quantity);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}
