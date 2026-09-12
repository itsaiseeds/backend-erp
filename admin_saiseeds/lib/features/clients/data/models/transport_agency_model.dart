class TransportAgencyModel {
  final String name;
  final bool isPrimary;

  const TransportAgencyModel({this.name = '', this.isPrimary = false});

  factory TransportAgencyModel.fromJson(Map<String, dynamic> json) {
    return TransportAgencyModel(
      name: json['name'] as String? ?? '',
      isPrimary: json['is_primary'] == true,
    );
  }

  Map<String, dynamic> toWriteJson() => {'name': name, 'is_primary': isPrimary};
}
