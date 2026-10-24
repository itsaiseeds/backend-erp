import '../../../../core/network/api_config.dart';

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
  final String packetWeight;
  final int packets;
  final String totalWeight;
  final String sellingPrice;

  /// The packaging's own image, "" if it has none.
  final String imageUrl;

  /// The image to show: the packaging's own, else the product's.
  final String displayImageUrl;

  const ProductPackagingModel({
    required this.publicId,
    this.product,
    this.packetWeight = '',
    this.packets = 0,
    this.totalWeight = '',
    this.sellingPrice = '',
    this.imageUrl = '',
    this.displayImageUrl = '',
  });

  factory ProductPackagingModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return ProductPackagingModel(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? PackagingProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
      packets: _countOf(json['packets']),
      totalWeight: _decimalOf(json['total_weight']),
      sellingPrice: _decimalOf(json['selling_price']),
      imageUrl: json['image_url'] as String? ?? '',
      displayImageUrl: json['display_image_url'] as String? ?? '',
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  String get packetsLabel => packets == 0 ? '' : '$packets';

  num? get packetWeightValue => num.tryParse(packetWeight);

  num? get totalWeightValue => num.tryParse(totalWeight);

  num? get sellingPriceValue => num.tryParse(sellingPrice);

  /// Absolute URL for [imageUrl] (the packaging's own image only -- blank
  /// when it falls back to the product's), which the API returns as a
  /// /media/... path.
  String get imageDisplayUrl => _absoluteUrl(imageUrl);

  /// Absolute URL for [displayImageUrl] -- the packaging's image, else the
  /// product's. What the edit dialog's preview should show.
  String get resolvedDisplayImageUrl => _absoluteUrl(displayImageUrl);

  static String _absoluteUrl(String path) {
    final String trimmed = path.trim();
    if (trimmed.isEmpty) return '';
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    final String base = ApiConfig.baseUrl;
    if (base.isEmpty) return trimmed;
    return trimmed.startsWith('/') ? '$base$trimmed' : '$base/$trimmed';
  }

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

class ProductPackagingImageUpload {
  final List<int> bytes;
  final String filename;

  const ProductPackagingImageUpload({
    required this.bytes,
    required this.filename,
  });
}
