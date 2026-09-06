import '../../../../core/models/city_model.dart';
import '../../../../core/models/created_by_model.dart';

class SalesPersonModel {
  final String id;
  final String name;
  final String email;
  final String phoneNumber;
  final String role;
  final CreatedByModel? createdBy;
  final String createdAt;
  final CityModel? city;
  final String provisioningUri;

  const SalesPersonModel({
    required this.id,
    required this.name,
    this.email = '',
    this.phoneNumber = '',
    this.role = '',
    this.createdBy,
    this.createdAt = '',
    this.city,
    this.provisioningUri = '',
  });

  factory SalesPersonModel.fromJson(Map<String, dynamic> json) {
    final dynamic createdBy = json['created_by'];
    final dynamic city = json['city'];
    final dynamic totp = json['totp'];

    return SalesPersonModel(
      id: '${json['id'] ?? ''}',
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      role: json['role'] as String? ?? '',
      createdBy: createdBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(createdBy))
          : null,
      createdAt: json['created_at'] as String? ?? '',
      city: city is Map
          ? CityModel.fromJson(Map<String, dynamic>.from(city))
          : null,
      provisioningUri: totp is Map
          ? (totp['provisioning_uri'] as String? ?? '')
          : '',
    );
  }

  String get createdByName => createdBy?.name ?? '';

  String get cityName => city?.name ?? '';

  int? get cityId => city?.id;
}
