import 'order_status.dart';

class OrderRefModel {
  final String publicId;
  final String name;

  const OrderRefModel({this.publicId = '', this.name = ''});

  factory OrderRefModel.fromJson(Map<String, dynamic> json) {
    return OrderRefModel(
      publicId: json['public_id'] as String? ?? '',
      name: json['company_name'] as String? ?? json['name'] as String? ?? '',
    );
  }
}

class OrderCityModel {
  final int id;
  final String name;

  const OrderCityModel({this.id = 0, this.name = ''});

  factory OrderCityModel.fromJson(Map<String, dynamic> json) {
    return OrderCityModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
    );
  }
}

class OrderAgencyModel {
  final int id;
  final String name;

  const OrderAgencyModel({this.id = 0, this.name = ''});

  factory OrderAgencyModel.fromJson(Map<String, dynamic> json) {
    return OrderAgencyModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
    );
  }
}

class OrderPackagingModel {
  final String publicId;
  final String productPublicId;
  final String productName;
  final String imageUrl;
  final num packetWeight;
  final int packets;
  final num totalWeight;
  final num sellingPrice;
  final num negotiatedSellingPrice;
  final int quantity;

  const OrderPackagingModel({
    this.publicId = '',
    this.productPublicId = '',
    this.productName = '',
    this.imageUrl = '',
    this.packetWeight = 0,
    this.packets = 0,
    this.totalWeight = 0,
    this.sellingPrice = 0,
    this.negotiatedSellingPrice = 0,
    this.quantity = 0,
  });

  factory OrderPackagingModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final Map<String, dynamic> productMap = product is Map
        ? Map<String, dynamic>.from(product)
        : const {};

    return OrderPackagingModel(
      publicId: json['public_id'] as String? ?? '',
      productPublicId: productMap['public_id'] as String? ?? '',
      productName: productMap['name'] as String? ?? '',
      imageUrl: productMap['image_url'] as String? ?? '',
      packetWeight: _asNum(json['packet_weight']),
      packets: _asInt(json['packets']),
      totalWeight: _asNum(json['total_weight']),
      sellingPrice: _asNum(json['selling_price']),
      negotiatedSellingPrice: _asNum(json['negotiated_selling_price']),
      quantity: _asInt(json['quantity']),
    );
  }

  num get effectivePrice =>
      negotiatedSellingPrice > 0 ? negotiatedSellingPrice : sellingPrice;

  num get lineTotal => effectivePrice * quantity;

  bool get isNegotiated =>
      negotiatedSellingPrice > 0 &&
      sellingPrice > 0 &&
      negotiatedSellingPrice != sellingPrice;

  String get packetSummary => '$packets x ${_trim(packetWeight)} kg';

  String get totalWeightSummary => '${_trim(totalWeight)} Kg';

  OrderPackagingModel copyWith({int? quantity, num? negotiatedSellingPrice}) {
    return OrderPackagingModel(
      publicId: publicId,
      productPublicId: productPublicId,
      productName: productName,
      imageUrl: imageUrl,
      packetWeight: packetWeight,
      packets: packets,
      totalWeight: totalWeight,
      sellingPrice: sellingPrice,
      negotiatedSellingPrice:
          negotiatedSellingPrice ?? this.negotiatedSellingPrice,
      quantity: quantity ?? this.quantity,
    );
  }

  static const int PRICE_DECIMALS = 2;

  Map<String, dynamic> toEditJson() => {
    'product_packaging_public_id': publicId,
    'quantity': quantity,
    'negotiated_selling_price': effectivePrice.toStringAsFixed(PRICE_DECIMALS),
  };

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}

class OrderModel {
  static const String DISPATCH_AGENCY = 'AGENCY';

  final String publicId;
  final DateTime? createdAt;
  final OrderStatus status;
  final OrderRefModel client;
  final String clientCreatedBy;
  final String createdBy;
  final String verifiedBy;
  final String deliveryAddress;
  final OrderCityModel? city;
  final OrderAgencyModel? transportAgency;
  final String dispatchMode;
  final DateTime? expectedDeliveryDate;
  final num totalAmount;
  final int totalPackets;
  final int itemCount;
  final List<OrderPackagingModel> packagings;

  const OrderModel({
    this.publicId = '',
    this.createdAt,
    this.status = OrderStatus.unknown,
    this.client = const OrderRefModel(),
    this.clientCreatedBy = '',
    this.createdBy = '',
    this.verifiedBy = '',
    this.deliveryAddress = '',
    this.city,
    this.transportAgency,
    this.dispatchMode = '',
    this.expectedDeliveryDate,
    this.totalAmount = 0,
    this.totalPackets = 0,
    this.itemCount = 0,
    this.packagings = const [],
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];
    final dynamic agency = json['transport_agency'];
    final dynamic client = json['client'];

    return OrderModel(
      publicId: json['public_id'] as String? ?? '',
      createdAt: _parseInstant(json['created_at']),
      status: OrderStatusX.fromRaw(json['status'] as String? ?? ''),
      client: client is Map
          ? OrderRefModel.fromJson(Map<String, dynamic>.from(client))
          : const OrderRefModel(),
      clientCreatedBy: json['client_created_by'] as String? ?? '',
      createdBy: json['created_by'] as String? ?? '',
      verifiedBy: json['verified_by'] as String? ?? '',
      deliveryAddress: json['delivery_address'] as String? ?? '',
      city: city is Map
          ? OrderCityModel.fromJson(Map<String, dynamic>.from(city))
          : null,
      transportAgency: agency is Map
          ? OrderAgencyModel.fromJson(Map<String, dynamic>.from(agency))
          : null,
      dispatchMode: json['dispatch_mode'] as String? ?? '',
      expectedDeliveryDate: _parseDateOnly(json['expected_delivery_date']),
      totalAmount: _asNum(json['total_amount']),
      totalPackets: _asInt(json['total_packets']),
      itemCount: _asInt(json['item_count']),
      packagings: json['packagings'] is List
          ? (json['packagings'] as List)
                .whereType<Map>()
                .map(
                  (entry) => OrderPackagingModel.fromJson(
                    Map<String, dynamic>.from(entry),
                  ),
                )
                .toList()
          : const [],
    );
  }

  bool get isAgencyDispatch => dispatchMode.toUpperCase() == DISPATCH_AGENCY;

  String get cityName => city?.name ?? '';

  String get agencyName => transportAgency?.name ?? '';

  int get bagCount =>
      packagings.fold(0, (total, line) => total + line.quantity);

  bool get canVerify => OrderStatusX.canVerify(status);

  bool get canUnverify => OrderStatusX.canUnverify(status);

  bool get canHold => OrderStatusX.canHold(status);

  bool get canReject => OrderStatusX.canReject(status);

  bool get canEdit => OrderStatusX.canEdit(status);

  static DateTime? _parseInstant(dynamic value) {
    final String raw = value == null ? '' : '$value'.trim();
    if (raw.isEmpty) return null;
    return DateTime.tryParse(raw)?.toUtc();
  }

  static DateTime? _parseDateOnly(dynamic value) {
    final String raw = value == null ? '' : '$value'.trim();
    if (raw.isEmpty) return null;
    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed == null) return null;
    return DateTime.utc(parsed.year, parsed.month, parsed.day);
  }
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
