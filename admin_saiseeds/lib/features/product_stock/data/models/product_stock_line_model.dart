enum ProductStockKind { bag, loose }

class ProductStockLineModel {
  final String publicId;
  final String name;
  final String snapshotDate;
  final int onHand;
  final int reserved;
  final int consumed;
  final int available;
  final ProductStockKind kind;
  final String packetWeight;

  const ProductStockLineModel({
    required this.publicId,
    required this.kind,
    this.name = '',
    this.snapshotDate = '',
    this.onHand = 0,
    this.reserved = 0,
    this.consumed = 0,
    this.available = 0,
    this.packetWeight = '',
  });

  factory ProductStockLineModel.fromJson(
    Map<String, dynamic> json, {
    required ProductStockKind kind,
    String packetWeight = '',
    String fallbackName = '',
  }) {
    final String name = json['name'] as String? ?? '';

    return ProductStockLineModel(
      publicId: '${json['public_id'] ?? ''}',
      kind: kind,
      name: name.trim().isEmpty ? fallbackName : name,
      snapshotDate: '${json['snapshot_date'] ?? ''}',
      onHand: _countOf(json['on_hand']),
      reserved: _countOf(json['reserved']),
      consumed: _countOf(json['consumed']),
      available: _countOf(json['available']),
      packetWeight: packetWeight,
    );
  }

  bool get isBag => kind == ProductStockKind.bag;

  num? get packetWeightValue => num.tryParse(packetWeight);

  DateTime? get snapshotDateTime => DateTime.tryParse(snapshotDate);

  static int _countOf(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
