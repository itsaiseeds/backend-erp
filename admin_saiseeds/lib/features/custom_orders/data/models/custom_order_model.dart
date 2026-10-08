import '../../../../core/services/products_service.dart';
import '../../../orders/data/models/child_org_model.dart';
import '../../../orders/data/models/order_status.dart';

class CustomOrderClientRef {
  final String publicId;
  final String companyName;

  const CustomOrderClientRef({this.publicId = '', this.companyName = ''});

  factory CustomOrderClientRef.fromJson(Map<String, dynamic> json) {
    return CustomOrderClientRef(
      publicId: '${json['public_id'] ?? ''}',
      companyName: json['company_name'] as String? ?? '',
    );
  }
}

class CustomOrderCityRef {
  final int id;
  final String name;

  const CustomOrderCityRef({this.id = 0, this.name = ''});

  factory CustomOrderCityRef.fromJson(Map<String, dynamic> json) {
    return CustomOrderCityRef(
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

class CustomOrderProductRef {
  final String publicId;
  final String name;
  final String imageUrl;

  const CustomOrderProductRef({
    this.publicId = '',
    this.name = '',
    this.imageUrl = '',
  });

  factory CustomOrderProductRef.fromJson(Map<String, dynamic> json) {
    return CustomOrderProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
      imageUrl: json['image_url'] as String? ?? '',
    );
  }
}

class CustomOrderItemModel {
  final CustomOrderProductRef? product;
  final String packetWeight;
  final String negotiatedSellingPrice;
  final int packets;
  final String lineTotal;

  const CustomOrderItemModel({
    this.product,
    this.packetWeight = '',
    this.negotiatedSellingPrice = '',
    this.packets = 0,
    this.lineTotal = '',
  });

  factory CustomOrderItemModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return CustomOrderItemModel(
      product: product is Map
          ? CustomOrderProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
      negotiatedSellingPrice: _decimalOf(json['negotiated_selling_price']),
      packets: _asInt(json['packets']),
      lineTotal: _decimalOf(json['line_total']),
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  /// The detail endpoint omits image_url, so the products cache fills in for
  /// a line opened from there.
  String get imageUrl {
    final String direct = product?.imageUrl.trim() ?? '';
    if (direct.isNotEmpty) return direct;
    return ProductsService.instance
            .productByPublicId(productPublicId)
            ?.imageUrl ??
        '';
  }

  num? get priceValue => num.tryParse(negotiatedSellingPrice);

  num get lineTotalValue {
    final num price = num.tryParse(negotiatedSellingPrice) ?? 0;
    return price * packets;
  }

  Map<String, dynamic> toRequestJson() => {
    'product_public_id': productPublicId,
    'packet_weight': packetWeight,
    'packets': packets,
    'negotiated_selling_price': negotiatedSellingPrice,
  };

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class CustomOrderModel {
  final String publicId;
  final String createdAt;
  final String status;
  final CustomOrderClientRef? client;
  final String clientCreatedBy;
  final String createdBy;
  final String verifiedBy;
  final String deliveryAddress;
  final ChildOrgModel? bookedFor;
  final CustomOrderCityRef? city;
  final String expectedDeliveryDate;
  final String actualDeliveryDate;
  final String specialComments;
  final String totalAmount;
  final int totalPackets;
  final int itemCount;
  final List<CustomOrderItemModel> items;

  const CustomOrderModel({
    required this.publicId,
    this.createdAt = '',
    this.status = '',
    this.client,
    this.clientCreatedBy = '',
    this.createdBy = '',
    this.verifiedBy = '',
    this.deliveryAddress = '',
    this.bookedFor,
    this.city,
    this.expectedDeliveryDate = '',
    this.actualDeliveryDate = '',
    this.specialComments = '',
    this.totalAmount = '',
    this.totalPackets = 0,
    this.itemCount = 0,
    this.items = const [],
  });

  factory CustomOrderModel.fromJson(Map<String, dynamic> json) {
    final dynamic client = json['client'];
    final dynamic city = json['city'];
    final dynamic items = json['items'];
    final dynamic bookedFor = json['booked_for'];

    // The list and detail payloads carry these differently: the list sends
    // created_by / created_at / city at the top level, the detail nests the
    // first under client, omits created_at, and leaves the city to the
    // address. Reading both keeps one model usable for either.
    final Map<String, dynamic> clientMap = client is Map
        ? Map<String, dynamic>.from(client)
        : const {};

    final List<CustomOrderItemModel> lines = items is List
        ? items
              .whereType<Map>()
              .map(
                (item) => CustomOrderItemModel.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList()
        : const [];

    return CustomOrderModel(
      publicId: '${json['public_id'] ?? ''}',
      createdAt: '${json['created_at'] ?? json['verified_at'] ?? ''}',
      status: '${json['status'] ?? ''}',
      client: client is Map
          ? CustomOrderClientRef.fromJson(Map<String, dynamic>.from(client))
          : null,
      clientCreatedBy: json['client_created_by'] as String? ?? '',
      createdBy:
          json['created_by'] as String? ??
          clientMap['created_by'] as String? ??
          '',
      verifiedBy:
          json['verified_by'] as String? ??
          clientMap['verified_by'] as String? ??
          '',
      deliveryAddress: json['delivery_address'] as String? ?? '',
      bookedFor: bookedFor is Map
          ? ChildOrgModel.fromJson(Map<String, dynamic>.from(bookedFor))
          : null,
      city: city is Map
          ? CustomOrderCityRef.fromJson(Map<String, dynamic>.from(city))
          : null,
      expectedDeliveryDate: _dateOf(json['expected_delivery_date']),
      actualDeliveryDate: _dateOf(json['actual_delivery_date']),
      specialComments: json['special_comments'] as String? ?? '',
      totalAmount: _decimalOf(json['total_amount']),
      totalPackets: _asInt(json['total_packets']),
      // The list endpoint sends item_count; the detail one only sends items.
      itemCount: json.containsKey('item_count')
          ? _asInt(json['item_count'])
          : lines.length,
      items: lines,
    );
  }

  String get clientName => client?.companyName ?? '';

  String get clientPublicId => client?.publicId ?? '';

  /// The detail payload has no city object -- it only names the city inside
  /// the delivery address -- so that is the fallback.
  String get cityName {
    final String named = city?.name.trim() ?? '';
    if (named.isNotEmpty) return named;
    return _cityFromAddress;
  }

  /// Same "don't repeat the column" rule as [OrderModel.deliveryToLabel].
  String get deliveryToLabel =>
      bookedFor != null ? bookedFor!.displayLabel : deliveryAddress;

  String get _cityFromAddress {
    final List<String> parts = deliveryAddress
        .split(',')
        .map((part) => part.trim())
        .where((part) => part.isNotEmpty)
        .toList();
    // "line 1, Rajkot, Gujarat, India" -- the city sits third from the end.
    if (parts.length < 3) return '';
    return parts[parts.length - 3];
  }

  OrderStatus get statusValue => OrderStatusX.fromRaw(status);

  bool get canDispatch => OrderStatusX.canDispatch(statusValue);

  bool get canRevertDispatch => OrderStatusX.canRevertDispatch(statusValue);

  /// Only an order that has not gone out may be removed; once dispatched the
  /// API refuses the delete.
  bool get canDelete => !OrderStatusX.canRevertDispatch(statusValue);

  DateTime? get createdAtDateTime => DateTime.tryParse(createdAt);

  DateTime? get expectedDeliveryDateTime =>
      DateTime.tryParse(expectedDeliveryDate);

  num? get totalAmountValue => num.tryParse(totalAmount);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static String _dateOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
