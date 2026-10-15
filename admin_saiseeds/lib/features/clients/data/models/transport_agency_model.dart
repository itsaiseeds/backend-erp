class TransportAgencyModel {
  /// The `ClientTransportAgency` *link* row's id -- not the underlying
  /// `TransportAgency`'s own id. This is deliberate: every existing write
  /// that picks one of a client's agencies (e.g. `UpdateOrderView`'s
  /// `client_transport_agency_id`) is scoped to the client through this link
  /// id, the same way `client_address_id` is a `ClientAddress` link id
  /// rather than a raw `Address` id. `0` when parsed from a context that
  /// never sends it (the create/edit client form, which only round-trips
  /// `name`/`is_primary`).
  final int id;
  final String name;
  final bool isPrimary;

  const TransportAgencyModel({
    this.id = 0,
    this.name = '',
    this.isPrimary = false,
  });

  factory TransportAgencyModel.fromJson(Map<String, dynamic> json) {
    return TransportAgencyModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      isPrimary: json['is_primary'] == true,
    );
  }

  Map<String, dynamic> toWriteJson() => {'name': name, 'is_primary': isPrimary};

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
