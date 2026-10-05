import '../../../../core/models/created_by_model.dart';

class WasteProductRef {
  final String publicId;
  final String name;

  const WasteProductRef({required this.publicId, required this.name});

  factory WasteProductRef.fromJson(Map<String, dynamic> json) {
    return WasteProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class WasteModel {
  final String publicId;
  final WasteProductRef? product;
  final String quantityKg;
  final String reason;
  final String createdAt;
  final CreatedByModel? createdBy;

  const WasteModel({
    required this.publicId,
    this.product,
    this.quantityKg = '',
    this.reason = '',
    this.createdAt = '',
    this.createdBy,
  });

  factory WasteModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final dynamic createdBy = json['created_by'];

    return WasteModel(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? WasteProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      quantityKg: _textOf(json['quantity_kg']),
      reason: json['reason'] as String? ?? '',
      createdAt: _textOf(json['created_at']),
      createdBy: createdBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(createdBy))
          : null,
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  String get createdByName => createdBy?.name ?? '';

  bool get hasReason => reason.trim().isNotEmpty;

  num? get quantityValue => num.tryParse(quantityKg.trim());

  DateTime? get createdAtTime => DateTime.tryParse(createdAt);

  bool matchesSearch(String query) {
    final String needle = query.trim().toLowerCase();
    if (needle.isEmpty) return true;
    return productName.toLowerCase().contains(needle) ||
        reason.toLowerCase().contains(needle) ||
        publicId.toLowerCase().contains(needle) ||
        quantityKg.toLowerCase().contains(needle) ||
        createdByName.toLowerCase().contains(needle);
  }

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }
}
