import '../../../../core/models/crop_model.dart';

class FarmerVisitProductRef {
  final String publicId;
  final String name;

  const FarmerVisitProductRef({required this.publicId, required this.name});

  factory FarmerVisitProductRef.fromJson(Map<String, dynamic> json) {
    return FarmerVisitProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class FarmerVisitModel {
  final String publicId;
  final String farmerName;
  final String contactNumber;
  final String village;
  final String landAreaBigha;
  final List<CropModel> crops;
  final bool usesOurProducts;
  final List<FarmerVisitProductRef> products;
  final String createdAt;

  const FarmerVisitModel({
    required this.publicId,
    this.farmerName = '',
    this.contactNumber = '',
    this.village = '',
    this.landAreaBigha = '',
    this.crops = const [],
    this.usesOurProducts = false,
    this.products = const [],
    this.createdAt = '',
  });

  factory FarmerVisitModel.fromJson(Map<String, dynamic> json) {
    return FarmerVisitModel(
      publicId: '${json['public_id'] ?? ''}',
      farmerName: '${json['farmer_name'] ?? ''}',
      contactNumber: '${json['contact_number'] ?? ''}',
      village: '${json['village'] ?? ''}',
      landAreaBigha: _decimalOf(json['land_area_bigha']),
      crops: _listOf(json['crops'], CropModel.fromJson),
      usesOurProducts: json['uses_our_products'] == true,
      products: _listOf(json['products'], FarmerVisitProductRef.fromJson),
      createdAt: '${json['created_at'] ?? ''}',
    );
  }

  String get cropNames => crops.map((crop) => crop.name).join(', ');

  String get productNames => products.map((product) => product.name).join(', ');

  num? get landAreaValue => num.tryParse(landAreaBigha);

  DateTime? get createdDateTime => DateTime.tryParse(createdAt);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value.trim();
    return '$value';
  }

  static List<T> _listOf<T>(
    dynamic value,
    T Function(Map<String, dynamic>) parser,
  ) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((entry) => parser(Map<String, dynamic>.from(entry)))
        .toList();
  }
}
