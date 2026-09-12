class ClientAddressModel {
  final String label;
  final String line1;
  final String line2;
  final String pincode;
  final String cityName;
  final String stateName;
  final String countryName;
  final int cityId;
  final int stateId;
  final int countryId;
  final bool isPrimary;

  ClientAddressModel copyWith({
    String? label,
    String? line1,
    String? line2,
    String? pincode,
    String? cityName,
    String? stateName,
    String? countryName,
    int? cityId,
    int? stateId,
    int? countryId,
    bool? isPrimary,
  }) {
    return ClientAddressModel(
      label: label ?? this.label,
      line1: line1 ?? this.line1,
      line2: line2 ?? this.line2,
      pincode: pincode ?? this.pincode,
      cityName: cityName ?? this.cityName,
      stateName: stateName ?? this.stateName,
      countryName: countryName ?? this.countryName,
      cityId: cityId ?? this.cityId,
      stateId: stateId ?? this.stateId,
      countryId: countryId ?? this.countryId,
      isPrimary: isPrimary ?? this.isPrimary,
    );
  }

  const ClientAddressModel({
    this.label = '',
    this.line1 = '',
    this.line2 = '',
    this.pincode = '',
    this.cityName = '',
    this.stateName = '',
    this.countryName = '',
    this.cityId = 0,
    this.stateId = 0,
    this.countryId = 0,
    this.isPrimary = false,
  });

  factory ClientAddressModel.fromJson(Map<String, dynamic> json) {
    return ClientAddressModel(
      label: json['label'] as String? ?? '',
      line1: json['line_1'] as String? ?? '',
      line2: json['line_2'] as String? ?? '',
      pincode: json['pincode'] as String? ?? '',
      cityName: _nameOf(json['city']),
      stateName: _nameOf(json['state']),
      countryName: _nameOf(json['country']),
      cityId: _idOf(json['city_id'] ?? json['city']),
      stateId: _idOf(json['state_id'] ?? json['state']),
      countryId: _idOf(json['country_id'] ?? json['country']),
      isPrimary: json['is_primary'] == true,
    );
  }

  Map<String, dynamic> toWriteJson() => {
    'line_1': line1,
    'line_2': line2,
    'pincode': pincode,
    'city': cityId,
    'state': stateId,
    'country': countryId,
    'label': label,
    'is_primary': isPrimary,
  };

  static String _nameOf(dynamic value) {
    if (value is Map) return value['name'] as String? ?? '';
    if (value is String) return value;
    return '';
  }

  static int _idOf(dynamic value) {
    if (value is Map) return _asInt(value['id']);
    return _asInt(value);
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  String get formatted => [
    line1,
    line2,
    cityName,
    stateName,
    pincode,
  ].where((part) => part.trim().isNotEmpty).join(', ');
}
