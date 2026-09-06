import 'city_model.dart';

class StateModel {
  final int id;
  final String name;
  final List<CityModel> cities;

  const StateModel({
    required this.id,
    required this.name,
    this.cities = const [],
  });

  factory StateModel.fromJson(Map<String, dynamic> json) {
    final String stateName = json['name'] as String? ?? '';
    final dynamic rawCities = json['cities'];

    return StateModel(
      id: _parseId(json['id']),
      name: stateName,
      cities: rawCities is List
          ? rawCities
                .whereType<Map>()
                .map(
                  (city) => CityModel.fromJson(
                    Map<String, dynamic>.from(city),
                    stateName: stateName,
                  ),
                )
                .toList()
          : const [],
    );
  }

  static int _parseId(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
