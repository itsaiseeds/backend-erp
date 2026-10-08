import 'child_org_model.dart';
import 'order_status.dart';
import '../../../return_orders/data/models/return_order_model.dart';
import '../../../return_orders/data/models/return_order_status.dart';

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
  final ChildOrgModel? bookedFor;
  final OrderCityModel? city;
  final OrderAgencyModel? transportAgency;
  final String dispatchMode;
  final DateTime? expectedDeliveryDate;
  final num totalAmount;
  final int totalPackets;
  final int itemCount;
  final List<OrderPackagingModel> packagings;
  final String specialComments;

  /// The returns raised against this order, in the order the detail endpoint
  /// sends them. One return is the common case; the payload still allows a list.
  final List<ReturnOrderModel> returns;

  const OrderModel({
    this.publicId = '',
    this.createdAt,
    this.status = OrderStatus.unknown,
    this.client = const OrderRefModel(),
    this.clientCreatedBy = '',
    this.createdBy = '',
    this.verifiedBy = '',
    this.deliveryAddress = '',
    this.bookedFor,
    this.city,
    this.transportAgency,
    this.dispatchMode = '',
    this.expectedDeliveryDate,
    this.totalAmount = 0,
    this.totalPackets = 0,
    this.itemCount = 0,
    this.packagings = const [],
    this.specialComments = '',
    this.returns = const [],
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];
    final dynamic agency = json['transport_agency'];
    final dynamic client = json['client'];
    final dynamic bookedFor = json['booked_for'];

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
      bookedFor: bookedFor is Map
          ? ChildOrgModel.fromJson(Map<String, dynamic>.from(bookedFor))
          : null,
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
      specialComments: json['special_comments'] as String? ?? '',
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
      returns: _returnList(json['return_order']),
    );
  }

  /// The detail endpoint embeds the return (or returns) against this order.
  /// A single object is the current shape; a list is accepted so the model does
  /// not break if the backend ever returns several.
  static List<ReturnOrderModel> _returnList(dynamic value) {
    if (value is Map) {
      return [
        ReturnOrderModel.fromJson(Map<String, dynamic>.from(value)),
      ];
    }
    if (value is List) {
      return value
          .whereType<Map>()
          .map(
            (entry) => ReturnOrderModel.fromJson(Map<String, dynamic>.from(entry)),
          )
          .toList();
    }
    return const [];
  }

  /// The detail endpoint only carries what the list leaves out: the return
  /// block, transport, comments and dates. Merging fills those gaps without
  /// discarding a single field of the list row, because the two endpoints use
  /// different shapes for the goods (`items` vs `packagings`) and only the
  /// list one supplies identity fields the steps read.
  OrderModel mergedWithDetail(OrderModel detail) {
    final OrderModel base = this;

    return OrderModel(
      publicId:
          detail.publicId.isNotEmpty ? detail.publicId : base.publicId,
      createdAt: detail.createdAt ?? base.createdAt,
      status: detail.status != OrderStatus.unknown ? detail.status : base.status,
      client: detail.client.name.isNotEmpty ? detail.client : base.client,
      clientCreatedBy: detail.clientCreatedBy.isNotEmpty
          ? detail.clientCreatedBy
          : base.clientCreatedBy,
      createdBy:
          detail.createdBy.isNotEmpty ? detail.createdBy : base.createdBy,
      verifiedBy:
          detail.verifiedBy.isNotEmpty ? detail.verifiedBy : base.verifiedBy,
      deliveryAddress: detail.deliveryAddress.isNotEmpty
          ? detail.deliveryAddress
          : base.deliveryAddress,
      bookedFor: detail.bookedFor ?? base.bookedFor,
      city: detail.city ?? base.city,
      transportAgency: detail.transportAgency ?? base.transportAgency,
      dispatchMode: detail.dispatchMode.isNotEmpty
          ? detail.dispatchMode
          : base.dispatchMode,
      expectedDeliveryDate:
          detail.expectedDeliveryDate ?? base.expectedDeliveryDate,
      totalAmount: detail.totalAmount > 0 ? detail.totalAmount : base.totalAmount,
      totalPackets:
          detail.totalPackets > 0 ? detail.totalPackets : base.totalPackets,
      itemCount: detail.itemCount > 0 ? detail.itemCount : base.itemCount,
      packagings:
          detail.packagings.isNotEmpty ? detail.packagings : base.packagings,
      specialComments: detail.specialComments.isNotEmpty
          ? detail.specialComments
          : base.specialComments,
      // The return block is the detail-only payload; when it came back empty
      // there is nothing new to say, so the base (which never has one) wins.
      returns: detail.returns.isNotEmpty ? detail.returns : base.returns,
    );
  }

  bool get isAgencyDispatch => dispatchMode.toUpperCase() == DISPATCH_AGENCY;

  String get cityName => city?.name ?? '';

  /// The order table's "Delivery To" cell: the separate delivery place when
  /// one is set, else the plain delivery address -- never both, so the table
  /// never grows a second column for the same idea.
  String get deliveryToLabel =>
      bookedFor != null ? bookedFor!.displayLabel : deliveryAddress;

  String get agencyName => transportAgency?.name ?? '';

  int get bagCount =>
      packagings.fold(0, (total, line) => total + line.quantity);

  /// What of the order actually went out the door and stayed out: only accepted
  /// returns bring the goods back and so reduce the value of the sale.
  num get returnedAmount => returns
      .where((returnOrder) => returnOrder.status == ReturnOrderStatus.accepted)
      .fold(0, (total, returnOrder) => total + returnOrder.totalAmount);

  num get netSaleAmount => totalAmount - returnedAmount;

  bool get canVerify => OrderStatusX.canVerify(status);

  bool get canUnverify => OrderStatusX.canUnverify(status);

  bool get canHold => OrderStatusX.canHold(status);

  bool get canReject => OrderStatusX.canReject(status);

  bool get canDispatch => OrderStatusX.canDispatch(status);

  bool get canRevertDispatch => OrderStatusX.canRevertDispatch(status);

  bool get canUploadLr => OrderStatusX.canUploadLr(status);

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
