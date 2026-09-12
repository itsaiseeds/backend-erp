import 'client_address_model.dart';
import 'client_contact_model.dart';
import 'client_status.dart';
import 'transport_agency_model.dart';

class ClientModel {
  final String publicId;
  final String companyName;
  final String companyPhone;
  final String gstNumber;
  final ClientStatus status;
  final bool isVerified;
  final String verifiedAt;
  final String verifiedBy;
  final String createdBy;
  final String createdAt;
  final ClientAddressModel? primaryAddress;
  final ClientContactModel? primaryContact;
  final List<ClientAddressModel> addresses;
  final List<ClientContactModel> contacts;
  final List<TransportAgencyModel> transportAgencies;

  const ClientModel({
    required this.publicId,
    required this.companyName,
    this.companyPhone = '',
    this.gstNumber = '',
    this.status = ClientStatus.unknown,
    this.isVerified = false,
    this.verifiedAt = '',
    this.verifiedBy = '',
    this.createdBy = '',
    this.createdAt = '',
    this.primaryAddress,
    this.primaryContact,
    this.addresses = const [],
    this.contacts = const [],
    this.transportAgencies = const [],
  });

  factory ClientModel.fromJson(Map<String, dynamic> json) {
    final List<ClientAddressModel> addresses = _listOf(
      json['addresses'],
      ClientAddressModel.fromJson,
    );
    final List<ClientContactModel> contacts = _listOf(
      json['contacts'],
      ClientContactModel.fromJson,
    );

    return ClientModel(
      publicId: json['public_id'] as String? ?? '',
      companyName: json['company_name'] as String? ?? '',
      companyPhone: json['company_phone'] as String? ?? '',
      gstNumber: json['gst_number'] as String? ?? '',
      status: ClientStatusX.fromRaw(json['status'] as String? ?? ''),
      isVerified: json['is_verified'] == true,
      verifiedAt: json['verified_at'] as String? ?? '',
      verifiedBy: json['verified_by'] as String? ?? '',
      createdBy: json['created_by'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
      primaryAddress: json['primary_address'] is Map
          ? ClientAddressModel.fromJson(
              Map<String, dynamic>.from(json['primary_address'] as Map),
            )
          : _firstPrimary(addresses, (a) => a.isPrimary),
      primaryContact: json['primary_contact'] is Map
          ? ClientContactModel.fromJson(
              Map<String, dynamic>.from(json['primary_contact'] as Map),
            )
          : _firstPrimary(contacts, (c) => c.isPrimary),
      addresses: addresses,
      contacts: contacts,
      transportAgencies: _listOf(
        json['transport_agencies'],
        TransportAgencyModel.fromJson,
      ),
    );
  }

  ClientModel copyWith({
    String? companyName,
    String? companyPhone,
    String? gstNumber,
    List<ClientAddressModel>? addresses,
    List<ClientContactModel>? contacts,
    List<TransportAgencyModel>? transportAgencies,
  }) {
    return ClientModel(
      publicId: publicId,
      companyName: companyName ?? this.companyName,
      companyPhone: companyPhone ?? this.companyPhone,
      gstNumber: gstNumber ?? this.gstNumber,
      status: status,
      isVerified: isVerified,
      verifiedAt: verifiedAt,
      verifiedBy: verifiedBy,
      createdBy: createdBy,
      createdAt: createdAt,
      primaryAddress: primaryAddress,
      primaryContact: primaryContact,
      addresses: addresses ?? this.addresses,
      contacts: contacts ?? this.contacts,
      transportAgencies: transportAgencies ?? this.transportAgencies,
    );
  }

  Map<String, dynamic> toUpdateJson() => {
    'public_id': publicId,
    'company_name': companyName,
    'company_phone': companyPhone,
    'gst_number': gstNumber,
    'addresses': addresses.map((a) => a.toWriteJson()).toList(),
    'contacts': contacts.map((c) => c.toWriteJson()).toList(),
    'transport_agencies': transportAgencies
        .map((t) => t.toWriteJson())
        .toList(),
  };

  bool get isPending => status == ClientStatus.verificationPending;

  String get cityName => primaryAddress?.cityName ?? '';

  static List<T> _listOf<T>(
    dynamic value,
    T Function(Map<String, dynamic>) parser,
  ) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((entry) => parser(Map<String, dynamic>.from(entry)))
        .toList();
  }

  static T? _firstPrimary<T>(List<T> items, bool Function(T) isPrimary) {
    if (items.isEmpty) return null;
    for (final item in items) {
      if (isPrimary(item)) return item;
    }
    return items.first;
  }
}
