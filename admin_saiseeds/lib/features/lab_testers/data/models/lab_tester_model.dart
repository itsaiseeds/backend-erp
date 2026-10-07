import '../../../../core/models/created_by_model.dart';

class LabTesterModel {
  final String id;
  final String name;
  final String email;
  final String phoneNumber;
  final String role;
  final CreatedByModel? createdBy;
  final String createdAt;
  final String provisioningUri;
  final bool isAdmin;

  const LabTesterModel({
    required this.id,
    required this.name,
    this.email = '',
    this.phoneNumber = '',
    this.role = '',
    this.createdBy,
    this.createdAt = '',
    this.provisioningUri = '',
    this.isAdmin = false,
  });

  factory LabTesterModel.fromJson(Map<String, dynamic> json) {
    final dynamic createdBy = json['created_by'];
    final dynamic totp = json['totp'];

    return LabTesterModel(
      id: '${json['id'] ?? ''}',
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      role: json['role'] as String? ?? '',
      createdBy: createdBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(createdBy))
          : null,
      createdAt: json['created_at'] as String? ?? '',
      provisioningUri: totp is Map
          ? (totp['provisioning_uri'] as String? ?? '')
          : '',
      isAdmin: json['is_admin'] as bool? ?? false,
    );
  }

  String get createdByName => createdBy?.name ?? '';
}
