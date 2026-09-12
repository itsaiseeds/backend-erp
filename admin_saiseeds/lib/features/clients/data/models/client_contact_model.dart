class ClientContactModel {
  final String name;
  final String phoneNumber;
  final String role;
  final bool isPrimary;

  const ClientContactModel({
    this.name = '',
    this.phoneNumber = '',
    this.role = '',
    this.isPrimary = false,
  });

  factory ClientContactModel.fromJson(Map<String, dynamic> json) {
    return ClientContactModel(
      name: json['name'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      role: json['role'] as String? ?? '',
      isPrimary: json['is_primary'] == true,
    );
  }

  Map<String, dynamic> toWriteJson() => {
    'name': name,
    'phone_number': phoneNumber,
    'role': role,
    'is_primary': isPrimary,
  };
}
