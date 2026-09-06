class PackagingProductRef {
  final String publicId;
  final String name;

  const PackagingProductRef({required this.publicId, required this.name});

  factory PackagingProductRef.fromJson(Map<String, dynamic> json) {
    return PackagingProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class ProductPackagingModel {
  final String publicId;
  final PackagingProductRef? product;
  final String packingBagWeight;
  final int packingBags;
  final String totalWeight;
  final String sellingPrice;

  const ProductPackagingModel({
    required this.publicId,
    this.product,
    this.packingBagWeight = '',
    this.packingBags = 0,
    this.totalWeight = '',
    this.sellingPrice = '',
  });

  factory ProductPackagingModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return ProductPackagingModel(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? PackagingProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      packingBagWeight: _decimalOf(json['packing_bag_weight']),
      packingBags: _countOf(json['packing_bags']),
      totalWeight: _decimalOf(json['total_weight']),
      sellingPrice: _decimalOf(json['selling_price']),
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  String get packingBagsLabel => packingBags == 0 ? '' : '$packingBags';

  num? get packingBagWeightValue => num.tryParse(packingBagWeight);

  num? get totalWeightValue => num.tryParse(totalWeight);

  num? get sellingPriceValue => num.tryParse(sellingPrice);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static int _countOf(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
