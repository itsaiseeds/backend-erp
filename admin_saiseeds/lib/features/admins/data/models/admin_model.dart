import '../../../../core/models/created_by_model.dart';

class AdminModel {
  final String id;
  final String name;
  final String email;
  final String phoneNumber;
  final String role;
  final CreatedByModel? createdBy;
  final String createdAt;
  final bool canUpdateStockCount;
  final String provisioningUri;

  const AdminModel({
    required this.id,
    required this.name,
    this.email = '',
    this.phoneNumber = '',
    this.role = '',
    this.createdBy,
    this.createdAt = '',
    this.canUpdateStockCount = false,
    this.provisioningUri = '',
  });

  factory AdminModel.fromJson(Map<String, dynamic> json) {
    final dynamic createdBy = json['created_by'];
    final dynamic totp = json['totp'];

    return AdminModel(
      id: '${json['id'] ?? ''}',
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      role: json['role'] as String? ?? '',
      createdBy: createdBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(createdBy))
          : null,
      createdAt: json['created_at'] as String? ?? '',
      canUpdateStockCount: json['can_update_stock_count'] as bool? ?? false,
      provisioningUri: totp is Map
          ? (totp['provisioning_uri'] as String? ?? '')
          : '',
    );
  }

  String get createdByName => createdBy?.name ?? '';
}
