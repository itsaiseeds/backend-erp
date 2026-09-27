import '../../../product_packagings/data/models/product_packaging_model.dart';

class BagStockLineModel {
  final ProductPackagingModel? packaging;
  final int onHand;
  final int reserved;
  final int consumed;
  final int available;

  const BagStockLineModel({
    this.packaging,
    this.onHand = 0,
    this.reserved = 0,
    this.consumed = 0,
    this.available = 0,
  });

  factory BagStockLineModel.fromJson(Map<String, dynamic> json) {
    final dynamic packaging = json['packaging'];

    return BagStockLineModel(
      packaging: packaging is Map
          ? ProductPackagingModel.fromJson(Map<String, dynamic>.from(packaging))
          : null,
      onHand: _countOf(json['on_hand']),
      reserved: _countOf(json['reserved']),
      consumed: _countOf(json['consumed']),
      available: _countOf(json['available']),
    );
  }

  String get packagingPublicId => packaging?.publicId ?? '';

  String get productName => packaging?.productName ?? '';

  String get packetWeight => packaging?.packetWeight ?? '';

  int get packetsPerBag => packaging?.packets ?? 0;

  num? get packetWeightValue => packaging?.packetWeightValue;

  static int _countOf(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class BagStockSnapshotModel {
  final String snapshotDate;
  final List<BagStockLineModel> lines;

  const BagStockSnapshotModel({this.snapshotDate = '', this.lines = const []});

  factory BagStockSnapshotModel.fromJson(Map<String, dynamic> json) {
    final dynamic lines = json['lines'];

    return BagStockSnapshotModel(
      snapshotDate: '${json['snapshot_date'] ?? ''}',
      lines: lines is List
          ? lines
                .whereType<Map>()
                .map(
                  (line) =>
                      BagStockLineModel.fromJson(Map<String, dynamic>.from(line)),
                )
                .toList()
          : const [],
    );
  }
}
