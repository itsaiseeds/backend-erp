class CropModel {
  final int id;
  final String name;

  const CropModel({required this.id, required this.name});

  factory CropModel.fromJson(Map<String, dynamic> json) {
    return CropModel(
      id: _parseId(json['id']),
      name: json['name'] as String? ?? '',
    );
  }

  static int _parseId(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is CropModel && other.id == id);

  @override
  int get hashCode => id.hashCode;
}
