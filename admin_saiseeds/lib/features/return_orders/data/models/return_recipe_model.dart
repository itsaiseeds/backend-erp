import 'return_order_model.dart';

/// One recipe the admin may book a line's packing material against.
///
/// A deleted recipe is still offered: stock booked against a recipe that has
/// since been replaced has to keep counting, so filtering it out here would
/// quietly break the books.
class ReturnRecipeOptionModel {
  final String publicId;
  final int materialTypeId;
  final String materialTypeName;
  final String materialUnitType;
  final num quantity;
  final bool isDeleted;
  final DateTime? createdAt;
  final DateTime? deletedAt;

  const ReturnRecipeOptionModel({
    this.publicId = '',
    this.materialTypeId = 0,
    this.materialTypeName = '',
    this.materialUnitType = '',
    this.quantity = 0,
    this.isDeleted = false,
    this.createdAt,
    this.deletedAt,
  });

  factory ReturnRecipeOptionModel.fromJson(Map<String, dynamic> json) {
    final dynamic materialType = json['material_type'];
    final Map<String, dynamic> material = materialType is Map
        ? Map<String, dynamic>.from(materialType)
        : const {};

    return ReturnRecipeOptionModel(
      publicId: json['public_id'] as String? ?? '',
      materialTypeId: _asInt(material['id']),
      materialTypeName: material['name'] as String? ?? '',
      materialUnitType: material['unit_type'] as String? ?? '',
      quantity: _asNum(json['quantity']),
      isDeleted: json['is_deleted'] == true,
      createdAt: _parseInstant(json['created_at']),
      deletedAt: _parseInstant(json['deleted_at']),
    );
  }

  /// The unit the quantity is counted in, which is per type and not always kg.
  String get quantityLabel {
    final String amount = quantity == quantity.roundToDouble()
        ? quantity.toInt().toString()
        : quantity.toString();
    return '$amount $materialUnitType';
  }

  /// The API refuses two recipes of the same material type on one line, so the
  /// picker has to enforce it before the admin gets a 400.
  int get materialTypeKey => materialTypeId;
}

class ReturnRecipeLineModel {
  final ReturnProductRefModel product;
  final num packetWeight;
  final int packets;
  final List<ReturnRecipeOptionModel> recipes;

  const ReturnRecipeLineModel({
    this.product = const ReturnProductRefModel(),
    this.packetWeight = 0,
    this.packets = 0,
    this.recipes = const [],
  });

  factory ReturnRecipeLineModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final Map<String, dynamic> productMap = product is Map
        ? Map<String, dynamic>.from(product)
        : const {};

    return ReturnRecipeLineModel(
      product: ReturnProductRefModel.fromJson(productMap),
      packetWeight: _asNum(json['packet_weight']),
      packets: _asInt(json['packets']),
      recipes: json['recipes'] is List
          ? (json['recipes'] as List)
                .whereType<Map>()
                .map(
                  (entry) => ReturnRecipeOptionModel.fromJson(
                    Map<String, dynamic>.from(entry),
                  ),
                )
                .toList()
          : const [],
    );
  }

  String get packetWeightLabel {
    final String weight = packetWeight == packetWeight.roundToDouble()
        ? packetWeight.toInt().toString()
        : packetWeight.toString();
    return '$weight kg';
  }

  bool get hasRecipes => recipes.isNotEmpty;
}

/// The candidate recipes per line, grouped the way the picker shows them.
class ReturnOrderRecipesModel {
  final List<ReturnRecipeLineModel> lines;

  const ReturnOrderRecipesModel({this.lines = const []});

  factory ReturnOrderRecipesModel.fromJson(Map<String, dynamic> json) {
    return ReturnOrderRecipesModel(
      lines: json['lines'] is List
          ? (json['lines'] as List)
                .whereType<Map>()
                .map(
                  (entry) => ReturnRecipeLineModel.fromJson(
                    Map<String, dynamic>.from(entry),
                  ),
                )
                .toList()
          : const [],
    );
  }

  bool get isEmpty => lines.every((line) => !line.hasRecipes);
}

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

num _asNum(dynamic value) {
  if (value is num) return value;
  if (value is String) return num.tryParse(value.trim()) ?? 0;
  return 0;
}

DateTime? _parseInstant(dynamic value) {
  final String raw = value == null ? '' : '$value'.trim();
  if (raw.isEmpty) return null;
  return DateTime.tryParse(raw)?.toUtc();
}
