import '../../../clients/data/models/client_address_model.dart';

/// "Delivery To" in the UI, ``booked_for`` on the wire: a downstream party a
/// client books an order on behalf of.
///
/// A list/short row carries only [id], [partyName], [villageName]; the detail
/// shape adds [transportName], [contactNumber] and [address]. Both parse
/// through this one model -- the fields simply default empty/null when the
/// server sent the short form.
class ChildOrgModel {
  final int id;
  final String partyName;
  final String villageName;
  final String transportName;
  final String? contactNumber;
  final ClientAddressModel? address;

  const ChildOrgModel({
    required this.id,
    this.partyName = '',
    this.villageName = '',
    this.transportName = '',
    this.contactNumber,
    this.address,
  });

  factory ChildOrgModel.fromJson(Map<String, dynamic> json) {
    final dynamic address = json['address'];

    return ChildOrgModel(
      id: _asInt(json['id']),
      partyName: json['party_name'] as String? ?? '',
      villageName: json['village_name'] as String? ?? '',
      transportName: json['transport_name'] as String? ?? '',
      contactNumber: json['contact_number'] as String?,
      address: address is Map
          ? ClientAddressModel.fromJson(Map<String, dynamic>.from(address))
          : null,
    );
  }

  /// "PartyName, VillageName" -- what a table cell or summary line shows.
  String get displayLabel {
    final List<String> parts = [
      partyName.trim(),
      villageName.trim(),
    ].where((part) => part.isNotEmpty).toList();
    return parts.join(', ');
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
