class OldSalesPersonModel {
  final int id;
  final String name;
  final String phoneNumber;
  final String city;
  final bool isDeleted;
  final int clientCount;

  const OldSalesPersonModel({
    required this.id,
    required this.name,
    this.phoneNumber = '',
    this.city = '',
    this.isDeleted = false,
    this.clientCount = 0,
  });

  factory OldSalesPersonModel.fromJson(Map<String, dynamic> json) {
    return OldSalesPersonModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      city: json['city'] as String? ?? '',
      isDeleted: json['is_deleted'] == true,
      clientCount: _asInt(json['client_count']),
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}
