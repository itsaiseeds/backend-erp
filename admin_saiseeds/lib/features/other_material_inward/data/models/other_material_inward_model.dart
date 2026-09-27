class OtherInwardProductRef {
  final String publicId;
  final String name;

  const OtherInwardProductRef({required this.publicId, required this.name});

  factory OtherInwardProductRef.fromJson(Map<String, dynamic> json) {
    return OtherInwardProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class OtherInwardRecipeRef {
  final String publicId;
  final OtherInwardProductRef? product;
  final String packetWeight;

  const OtherInwardRecipeRef({
    required this.publicId,
    this.product,
    this.packetWeight = '',
  });

  factory OtherInwardRecipeRef.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return OtherInwardRecipeRef(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? OtherInwardProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
    );
  }

  String get productName => product?.name ?? '';

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}

class OtherInwardPartyRef {
  final int id;
  final String name;

  const OtherInwardPartyRef({required this.id, required this.name});

  factory OtherInwardPartyRef.fromJson(Map<String, dynamic> json) {
    return OtherInwardPartyRef(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class OtherMaterialInwardModel {
  final String publicId;
  final OtherInwardRecipeRef? recipe;
  final OtherInwardPartyRef? party;
  final String quantity;
  final String effectiveDate;

  const OtherMaterialInwardModel({
    required this.publicId,
    this.recipe,
    this.party,
    this.quantity = '',
    this.effectiveDate = '',
  });

  factory OtherMaterialInwardModel.fromJson(Map<String, dynamic> json) {
    final dynamic recipe = json['recipe'];
    final dynamic party = json['party'];

    return OtherMaterialInwardModel(
      publicId: '${json['public_id'] ?? ''}',
      recipe: recipe is Map
          ? OtherInwardRecipeRef.fromJson(Map<String, dynamic>.from(recipe))
          : null,
      party: party is Map
          ? OtherInwardPartyRef.fromJson(Map<String, dynamic>.from(party))
          : null,
      quantity: _decimalOf(json['quantity']),
      effectiveDate: '${json['effective_date'] ?? ''}',
    );
  }

  String get recipePublicId => recipe?.publicId ?? '';

  String get productName => recipe?.productName ?? '';

  String get packetWeight => recipe?.packetWeight ?? '';

  String get partyName => party?.name ?? '';

  int? get partyId => party?.id;

  num? get quantityValue => num.tryParse(quantity);

  DateTime? get effectiveDateTime => DateTime.tryParse(effectiveDate);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}
