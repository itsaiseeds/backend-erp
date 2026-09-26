import '../../../../core/models/city_model.dart';

class PartyModel {
  final int id;
  final String name;
  final CityModel? city;
  final String contactNumber;

  const PartyModel({
    required this.id,
    this.name = '',
    this.city,
    this.contactNumber = '',
  });

  factory PartyModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];

    return PartyModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      city: city is Map
          ? CityModel.fromJson(Map<String, dynamic>.from(city))
          : null,
      contactNumber: json['contact_number'] as String? ?? '',
    );
  }

  String get cityName => city?.name ?? '';

  int get cityId => city?.id ?? 0;

  Map<String, dynamic> toWriteJson() => {
    'name': name,
    'city': cityId,
    'contact_number': contactNumber.trim().isEmpty ? null : contactNumber,
  };

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}
