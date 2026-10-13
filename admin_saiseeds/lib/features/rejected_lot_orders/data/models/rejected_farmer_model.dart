class RejectedFarmerModel {
  final String farmerName;
  final int lotCount;
  final String quantityKg;
  final String remainingKg;

  const RejectedFarmerModel({
    this.farmerName = '',
    this.lotCount = 0,
    this.quantityKg = '',
    this.remainingKg = '',
  });

  factory RejectedFarmerModel.fromJson(Map<String, dynamic> json) {
    return RejectedFarmerModel(
      farmerName: json['farmer_name'] as String? ?? '',
      lotCount: _asInt(json['lot_count']),
      quantityKg: _decimalOf(json['quantity_kg']),
      remainingKg: _decimalOf(json['remaining_kg']),
    );
  }

  num get remainingKgValue => num.tryParse(remainingKg) ?? 0;

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
