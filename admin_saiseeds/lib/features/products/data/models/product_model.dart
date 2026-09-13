import '../../../../core/models/crop_model.dart';
import '../../../../core/network/api_config.dart';
import '../../../../core/models/stage_model.dart';

class ProductModel {
  final String publicId;
  final String name;
  final CropModel? crop;
  final StageModel? stage;
  final String sellingPrice;
  final String imageUrl;
  final List<String> descriptionItems;

  const ProductModel({
    required this.publicId,
    required this.name,
    this.crop,
    this.stage,
    this.sellingPrice = '',
    this.imageUrl = '',
    this.descriptionItems = const [],
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    final dynamic crop = json['crop'];
    final dynamic stage = json['stage'];

    return ProductModel(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
      crop: crop is Map
          ? CropModel.fromJson(Map<String, dynamic>.from(crop))
          : null,
      stage: stage is Map
          ? StageModel.fromJson(Map<String, dynamic>.from(stage))
          : Stages.byId(stage is num ? stage.toInt() : null),
      sellingPrice: _priceOf(json['selling_price']),
      imageUrl: json['image_url'] as String? ?? '',
      descriptionItems: _itemsOf(json['description_items']),
    );
  }

  String get cropName => crop?.name ?? '';

  int? get cropId => crop?.id;

  String get stageName => stage?.label ?? '';

  /// Absolute URL for [imageUrl], which the API returns as a /media/... path.
  String get imageDisplayUrl {
    final String path = imageUrl.trim();
    if (path.isEmpty) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;

    final String base = ApiConfig.baseUrl;
    if (base.isEmpty) return path;
    return path.startsWith('/') ? '$base$path' : '$base/$path';
  }

  int? get stageId => stage?.id;

  num? get sellingPriceValue => num.tryParse(sellingPrice);

  static List<String> _itemsOf(dynamic value) {
    if (value is! List) return const [];
    return value
        .map((item) => '$item'.trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }

  static String _priceOf(dynamic value) {
    if (value == null) return '';

    // The API sends a JSON number (30.0); a trailing .0 is noise in the UI,
    // while genuine paise (30.5) must survive.
    final num? parsed = value is num ? value : num.tryParse('$value');
    if (parsed == null) return '$value';
    return parsed == parsed.roundToDouble()
        ? parsed.toInt().toString()
        : '$parsed';
  }
}

class ProductImageUpload {
  final List<int> bytes;
  final String filename;

  const ProductImageUpload({required this.bytes, required this.filename});
}
