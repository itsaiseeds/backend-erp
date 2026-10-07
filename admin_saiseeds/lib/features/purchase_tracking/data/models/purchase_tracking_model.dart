import '../../../../core/models/created_by_model.dart';

/// Unit of measure for a [PurchaseTrackingModel]'s quantity -- mirrors the
/// server's `NonStockUnit` choices exactly (value and label are the same
/// string there, so no separate label map is needed).
class NonStockUnit {
  NonStockUnit._();

  static const String KG = 'kg';
  static const String G = 'g';
  static const String LITRE = 'litre';
  static const String ML = 'ml';
  static const String COUNT = 'count';
  static const String PACKET = 'packet';

  static const List<String> ALL = [KG, G, LITRE, ML, COUNT, PACKET];
}

/// One non-stock inward entry (`NS-…`): an incoming consumable that is not
/// seed stock -- pesticides, insecticides, spare parts, ... -- linked to
/// nothing (no product, party or stock ledger) and never counted in any
/// stock figure.
class PurchaseTrackingModel {
  final String publicId;
  final String name;
  final String description;
  final String companyName;
  final String? price;
  final String quantity;
  final String unit;
  final String createdAt;
  final CreatedByModel? createdBy;

  const PurchaseTrackingModel({
    required this.publicId,
    this.name = '',
    this.description = '',
    this.companyName = '',
    this.price,
    this.quantity = '',
    this.unit = NonStockUnit.KG,
    this.createdAt = '',
    this.createdBy,
  });

  factory PurchaseTrackingModel.fromJson(Map<String, dynamic> json) {
    final dynamic createdBy = json['created_by'];

    return PurchaseTrackingModel(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      companyName: json['company_name'] as String? ?? '',
      price: json['price'] as String?,
      quantity: _textOf(json['quantity']),
      unit: json['unit'] as String? ?? NonStockUnit.KG,
      createdAt: _textOf(json['created_at']),
      createdBy: createdBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(createdBy))
          : null,
    );
  }

  String get createdByName => createdBy?.name ?? '';

  bool get hasPrice => (price ?? '').trim().isNotEmpty;

  bool get hasDescription => description.trim().isNotEmpty;

  bool get hasCompanyName => companyName.trim().isNotEmpty;

  num? get priceValue => price == null ? null : num.tryParse(price!.trim());

  num? get quantityValue => num.tryParse(quantity.trim());

  DateTime? get createdAtTime => DateTime.tryParse(createdAt);

  bool matchesSearch(String query) {
    final String needle = query.trim().toLowerCase();
    if (needle.isEmpty) return true;
    return name.toLowerCase().contains(needle) ||
        companyName.toLowerCase().contains(needle) ||
        description.toLowerCase().contains(needle) ||
        publicId.toLowerCase().contains(needle) ||
        createdByName.toLowerCase().contains(needle);
  }

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }
}
