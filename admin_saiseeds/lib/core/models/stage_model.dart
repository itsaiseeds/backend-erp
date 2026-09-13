class StageModel {
  final int id;
  final String code;
  final String name;

  const StageModel({required this.id, this.code = '', this.name = ''});

  factory StageModel.fromJson(Map<String, dynamic> json) {
    return StageModel(
      id: _parseId(json['id']),
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
    );
  }

  String get label => name.isNotEmpty ? name : code;

  static int _parseId(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is StageModel && other.id == id);

  @override
  int get hashCode => id.hashCode;
}

class Stages {
  Stages._();

  static const StageModel breeder = StageModel(
    id: 1,
    code: 'BREEDER',
    name: 'Breeder',
  );
  static const StageModel foundation = StageModel(
    id: 2,
    code: 'FOUNDATION',
    name: 'Foundation',
  );
  static const StageModel research = StageModel(
    id: 3,
    code: 'RESEARCH',
    name: 'Research',
  );
  static const StageModel certified = StageModel(
    id: 4,
    code: 'CERTIFIED',
    name: 'Certified',
  );

  static const List<StageModel> all = [
    breeder,
    foundation,
    research,
    certified,
  ];

  static StageModel? byId(int? id) {
    if (id == null) return null;
    for (final stage in all) {
      if (stage.id == id) return stage;
    }
    return null;
  }
}
