import 'package:equatable/equatable.dart';

class AuthSession extends Equatable {
  final int userId;
  final String name;
  final String phoneNumber;
  final String role;
  final bool canCreateAdmin;
  final bool canCreateSalesPerson;

  const AuthSession({
    required this.userId,
    required this.name,
    required this.phoneNumber,
    required this.role,
    required this.canCreateAdmin,
    required this.canCreateSalesPerson,
  });

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    final user = json['user'];
    final Map<String, dynamic> userMap = user is Map
        ? Map<String, dynamic>.from(user)
        : Map<String, dynamic>.from(json);

    return AuthSession(
      userId: _asInt(userMap['id']),
      name: _asString(userMap['name']),
      phoneNumber: _asString(userMap['phone_number']),
      role: _asString(userMap['role']),
      canCreateAdmin: _asBool(
        json['can_create_admin'] ?? userMap['can_create_admin'],
      ),
      canCreateSalesPerson: _asBool(
        json['can_create_sales_person'] ?? userMap['can_create_sales_person'],
      ),
    );
  }

  Map<String, dynamic> toJson() => {
    'user': {
      'id': userId,
      'name': name,
      'phone_number': phoneNumber,
      'role': role,
    },
    'can_create_admin': canCreateAdmin,
    'can_create_sales_person': canCreateSalesPerson,
  };

  static String _asString(dynamic value) => value is String ? value : '';

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static bool _asBool(dynamic value) => value is bool && value;

  @override
  List<Object?> get props => [
    userId,
    name,
    phoneNumber,
    role,
    canCreateAdmin,
    canCreateSalesPerson,
  ];
}
