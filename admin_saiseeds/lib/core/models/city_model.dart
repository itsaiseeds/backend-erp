class CityModel {
  final int id;
  final String name;
  final String stateName;

  const CityModel({
    required this.id,
    required this.name,
    this.stateName = '',
  });

  factory CityModel.fromJson(
    Map<String, dynamic> json, {
    String stateName = '',
  }) {
    return CityModel(
      id: _parseId(json['id']),
      name: json['name'] as String? ?? '',
      stateName: stateName,
    );
  }

  static int _parseId(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is CityModel && other.id == id);

  @override
  int get hashCode => id.hashCode;
}
