class CreatedByModel {
  final int id;
  final String name;

  const CreatedByModel({required this.id, required this.name});

  factory CreatedByModel.fromJson(Map<String, dynamic> json) {
    return CreatedByModel(
      id: _parseId(json['id']),
      name: json['name'] as String? ?? '',
    );
  }

  static int _parseId(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
