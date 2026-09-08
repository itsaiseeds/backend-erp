import '../../../../core/models/crop_model.dart';

class ProductModel {
  final String publicId;
  final String name;
  final CropModel? crop;
  final String buyingPrice;
  final String sellingPrice;
  final String marginPerPacket;

  const ProductModel({
    required this.publicId,
    required this.name,
    this.crop,
    this.buyingPrice = '',
    this.sellingPrice = '',
    this.marginPerPacket = '',
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    final dynamic crop = json['crop'];

    return ProductModel(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
      crop: crop is Map
          ? CropModel.fromJson(Map<String, dynamic>.from(crop))
          : null,
      buyingPrice: _priceOf(json['buying_price']),
      sellingPrice: _priceOf(json['selling_price']),
      marginPerPacket: _priceOf(json['margin_per_packet']),
    );
  }

  String get cropName => crop?.name ?? '';

  int? get cropId => crop?.id;

  num? get buyingPriceValue => num.tryParse(buyingPrice);

  num? get sellingPriceValue => num.tryParse(sellingPrice);

  num? get marginPerPacketValue => num.tryParse(marginPerPacket);

  static String _priceOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}
