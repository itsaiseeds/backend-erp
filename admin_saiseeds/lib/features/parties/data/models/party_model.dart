import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';

/// The two kinds of party. The API's filter and create/update payloads use
/// these wire values verbatim.
class PartyType {
  PartyType._();

  static const String RAW_MATERIAL = 'RAW_MATERIAL';
  static const String OTHER_MATERIAL = 'OTHER_MATERIAL';

  static const List<String> values = [RAW_MATERIAL, OTHER_MATERIAL];
}

class PartyModel {
  final int id;
  final String name;
  final CityModel? city;
  final String contactNumber;
  final String partyType;

  const PartyModel({
    required this.id,
    this.name = '',
    this.city,
    this.contactNumber = '',
    this.partyType = PartyType.RAW_MATERIAL,
  });

  factory PartyModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];

    return PartyModel(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      city: city is Map
          ? CityModel.fromJson(Map<String, dynamic>.from(city))
          : null,
      contactNumber: json['contact_number'] as String? ?? '',
      partyType: json['party_type'] as String? ?? PartyType.RAW_MATERIAL,
    );
  }

  String get cityName => city?.name ?? '';

  int get cityId => city?.id ?? 0;

  bool get isRawMaterial => partyType == PartyType.RAW_MATERIAL;

  bool get isOtherMaterial => partyType == PartyType.OTHER_MATERIAL;

  /// The display form of the wire value: "RAW_MATERIAL" -> "Raw Material".
  String get partyTypeLabel => switch (partyType) {
    PartyType.OTHER_MATERIAL => AppStrings.PARTY_TYPE_OTHER_MATERIAL,
    _ => AppStrings.PARTY_TYPE_RAW_MATERIAL,
  };

  Map<String, dynamic> toWriteJson() => {
    'name': name,
    'city': cityId,
    'contact_number': contactNumber.trim().isEmpty ? null : contactNumber,
    if (partyType.isNotEmpty) 'party_type': partyType,
  };

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}
