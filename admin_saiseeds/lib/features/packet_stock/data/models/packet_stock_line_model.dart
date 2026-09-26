class PacketStockProductRef {
  final String publicId;
  final String name;

  const PacketStockProductRef({required this.publicId, required this.name});

  factory PacketStockProductRef.fromJson(Map<String, dynamic> json) {
    return PacketStockProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class PacketStockLineModel {
  final PacketStockProductRef? product;
  final String packetWeight;
  final int onHand;
  final int reserved;
  final int consumed;
  final int available;

  const PacketStockLineModel({
    this.product,
    this.packetWeight = '',
    this.onHand = 0,
    this.reserved = 0,
    this.consumed = 0,
    this.available = 0,
  });

  factory PacketStockLineModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return PacketStockLineModel(
      product: product is Map
          ? PacketStockProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      packetWeight: _decimalOf(json['packet_weight']),
      onHand: _countOf(json['on_hand']),
      reserved: _countOf(json['reserved']),
      consumed: _countOf(json['consumed']),
      available: _countOf(json['available']),
    );
  }

  String get productPublicId => product?.publicId ?? '';

  String get productName => product?.name ?? '';

  num? get packetWeightValue => num.tryParse(packetWeight);

  String get poolKey => '$productPublicId|$packetWeight';

  static String poolKeyOf(String productPublicId, String packetWeight) =>
      '$productPublicId|$packetWeight';

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

class PacketStockSnapshotModel {
  final String snapshotDate;
  final List<PacketStockLineModel> lines;

  const PacketStockSnapshotModel({
    this.snapshotDate = '',
    this.lines = const [],
  });

  factory PacketStockSnapshotModel.fromJson(Map<String, dynamic> json) {
    final dynamic lines = json['lines'];

    return PacketStockSnapshotModel(
      snapshotDate: '${json['snapshot_date'] ?? ''}',
      lines: lines is List
          ? lines
                .whereType<Map>()
                .map(
                  (line) => PacketStockLineModel.fromJson(
                    Map<String, dynamic>.from(line),
                  ),
                )
                .toList()
          : const [],
    );
  }
}
