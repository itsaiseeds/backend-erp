import 'return_order_status.dart';

/// The order a return was raised against. Only the id and the order's own status
/// travel with a list row, which is all a table needs to say "which order, and
/// is it still in a state that could be returned".
class ReturnOrderRefModel {
  final String publicId;
  final String status;

  const ReturnOrderRefModel({this.publicId = '', this.status = ''});

  factory ReturnOrderRefModel.fromJson(Map<String, dynamic> json) {
    return ReturnOrderRefModel(
      publicId: json['public_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
    );
  }

  bool get isReturnable => status == 'DISPATCHED' || status == 'DELIVERED';
}

class ReturnClientRefModel {
  final String publicId;
  final String companyName;

  const ReturnClientRefModel({this.publicId = '', this.companyName = ''});

  factory ReturnClientRefModel.fromJson(Map<String, dynamic> json) {
    return ReturnClientRefModel(
      publicId: json['public_id'] as String? ?? '',
      companyName: json['company_name'] as String? ?? '',
    );
  }
}

class ReturnProductRefModel {
  final String publicId;
  final String name;

  const ReturnProductRefModel({this.publicId = '', this.name = ''});

  factory ReturnProductRefModel.fromJson(Map<String, dynamic> json) {
    return ReturnProductRefModel(
      publicId: json['public_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
    );
  }
}

/// A person on a return: who raised it, who accepted it, who rejected it. Null
/// on the payload rather than blank, so "nobody did yet" is distinguishable from
/// a name that failed to load.
class ReturnUserRefModel {
  final int id;
  final String name;

  const ReturnUserRefModel({this.id = 0, this.name = ''});

  factory ReturnUserRefModel.fromJson(Map<String, dynamic> json) {
    return ReturnUserRefModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
    );
  }
}

class ReturnOrderItemModel {
  final ReturnProductRefModel product;
  final num packetWeight;
  final int packets;
  final num kg;
  final num pricePerPacket;
  final num lineTotal;

  const ReturnOrderItemModel({
    this.product = const ReturnProductRefModel(),
    this.packetWeight = 0,
    this.packets = 0,
    this.kg = 0,
    this.pricePerPacket = 0,
    this.lineTotal = 0,
  });

  factory ReturnOrderItemModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final Map<String, dynamic> productMap = product is Map
        ? Map<String, dynamic>.from(product)
        : const {};

    return ReturnOrderItemModel(
      product: ReturnProductRefModel.fromJson(productMap),
      packetWeight: _asNum(json['packet_weight']),
      packets: _asInt(json['packets']),
      kg: _asNum(json['kg']),
      pricePerPacket: _asNum(json['price_per_packet']),
      lineTotal: _asNum(json['line_total']),
    );
  }

  String get packetWeightLabel => '${_trim(packetWeight)} kg';

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}

class ReturnOrderModel {
  final String publicId;
  final ReturnOrderStatus status;
  final DateTime? returnDate;
  final DateTime? createdAt;
  final ReturnOrderRefModel order;
  final ReturnClientRefModel client;
  final ReturnUserRefModel? createdBy;
  final ReturnUserRefModel? verifiedBy;
  final ReturnUserRefModel? rejectedBy;
  final DateTime? verifiedAt;
  final DateTime? rejectedAt;
  final List<ReturnOrderItemModel> items;
  final num totalKg;
  final num totalAmount;

  /// Only on the full payload, and only meaningful once the return has been
  /// accepted -- it records whether the packing material was booked too.
  final bool? includeInOtherRawMaterials;
  final List<String> inwardRawMaterials;
  final List<String> inwardOtherMaterials;

  const ReturnOrderModel({
    this.publicId = '',
    this.status = ReturnOrderStatus.unknown,
    this.returnDate,
    this.createdAt,
    this.order = const ReturnOrderRefModel(),
    this.client = const ReturnClientRefModel(),
    this.createdBy,
    this.verifiedBy,
    this.rejectedBy,
    this.verifiedAt,
    this.rejectedAt,
    this.items = const [],
    this.totalKg = 0,
    this.totalAmount = 0,
    this.includeInOtherRawMaterials,
    this.inwardRawMaterials = const [],
    this.inwardOtherMaterials = const [],
  });

  factory ReturnOrderModel.fromJson(Map<String, dynamic> json) {
    final dynamic order = json['order'];
    final dynamic client = json['client'];

    return ReturnOrderModel(
      publicId: json['public_id'] as String? ?? '',
      status: ReturnOrderStatusX.fromRaw(json['status'] as String? ?? ''),
      returnDate: _parseDateOnly(json['return_date']),
      createdAt: _parseInstant(json['created_at']),
      order: order is Map
          ? ReturnOrderRefModel.fromJson(Map<String, dynamic>.from(order))
          : const ReturnOrderRefModel(),
      client: client is Map
          ? ReturnClientRefModel.fromJson(Map<String, dynamic>.from(client))
          : const ReturnClientRefModel(),
      createdBy: _userOrNull(json['created_by']),
      verifiedBy: _userOrNull(json['verified_by']),
      rejectedBy: _userOrNull(json['rejected_by']),
      verifiedAt: _parseInstant(json['verified_at']),
      rejectedAt: _parseInstant(json['rejected_at']),
      items: json['items'] is List
          ? (json['items'] as List)
                .whereType<Map>()
                .map(
                  (entry) => ReturnOrderItemModel.fromJson(
                    Map<String, dynamic>.from(entry),
                  ),
                )
                .toList()
          : const [],
      totalKg: _asNum(json['total_kg']),
      totalAmount: _asNum(json['total_amount']),
      includeInOtherRawMaterials: json['include_in_other_raw_materials'] is bool
          ? json['include_in_other_raw_materials'] as bool
          : null,
      inwardRawMaterials: _stringList(json['inward_raw_materials']),
      inwardOtherMaterials: _stringList(json['inward_other_materials']),
    );
  }

  int get totalPackets => items.fold(0, (total, line) => total + line.packets);

  String get createdByName => createdBy?.name ?? '';

  String get verifiedByName => verifiedBy?.name ?? '';

  String get rejectedByName => rejectedBy?.name ?? '';

  bool get canAccept => ReturnOrderStatusX.canAccept(status);

  bool get canReject => ReturnOrderStatusX.canReject(status);

  bool get canUnreject => ReturnOrderStatusX.canUnreject(status);

  bool get canRevertAccept => ReturnOrderStatusX.canRevertAccept(status);

  bool get canEdit => ReturnOrderStatusX.canEdit(status);

  static ReturnUserRefModel? _userOrNull(dynamic value) {
    if (value is! Map) return null;
    return ReturnUserRefModel.fromJson(Map<String, dynamic>.from(value));
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) return const [];
    return value.map((entry) => '$entry').toList();
  }

  static DateTime? _parseInstant(dynamic value) {
    final String raw = value == null ? '' : '$value'.trim();
    if (raw.isEmpty) return null;
    return DateTime.tryParse(raw)?.toUtc();
  }

  /// A calendar date, kept at UTC midnight so the day never slides.
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
