import '../../../../core/models/crop_model.dart';
import 'farmer_visit_model.dart';
import 'field_trip_model.dart';

/// One trip on which this farmer was met, as it arrives inside a farmer row.
class FarmerVisitSummary {
  final String publicId;
  final String fieldTripPublicId;
  final String village;
  final String landAreaBigha;
  final List<CropModel> crops;
  final List<FarmerVisitProductRef> products;
  final FieldTripPersonRef? salesPerson;
  final String visitedAt;

  const FarmerVisitSummary({
    this.publicId = '',
    this.fieldTripPublicId = '',
    this.village = '',
    this.landAreaBigha = '',
    this.crops = const [],
    this.products = const [],
    this.salesPerson,
    this.visitedAt = '',
  });

  /// The nested visit shape is the farmer-visit payload with the trip and the
  /// salesperson folded in, so both spellings of each key are accepted.
  factory FarmerVisitSummary.fromJson(Map<String, dynamic> json) {
    final dynamic trip = json['field_trip'];
    final dynamic salesPerson = json['sales_person'] ?? json['created_by'];

    return FarmerVisitSummary(
      publicId: FarmerModel.stringOf(json['public_id']),
      fieldTripPublicId: trip is Map
          ? FarmerModel.stringOf(Map<String, dynamic>.from(trip)['public_id'])
          : FarmerModel.stringOf(json['field_trip_public_id'] ?? trip),
      village: FarmerModel.stringOf(json['village']),
      landAreaBigha: FarmerModel.decimalOf(json['land_area_bigha']),
      crops: FarmerModel.listOf(json['crops'], CropModel.fromJson),
      products: FarmerModel.listOf(
        json['products'],
        FarmerVisitProductRef.fromJson,
      ),
      salesPerson: salesPerson is Map
          ? FieldTripPersonRef.fromJson(Map<String, dynamic>.from(salesPerson))
          : null,
      visitedAt: FarmerModel.stringOf(json['visited_at'] ?? json['created_at']),
    );
  }

  String get salesPersonName => salesPerson?.name ?? '';

  DateTime? get visitedDateTime => DateTime.tryParse(visitedAt);
}

/// A farmer aggregated across every trip they were met on.
///
/// There is no public id on this record: the backend groups visits by
/// [contactNumber], which is therefore the row identity.
class FarmerModel {
  final String contactNumber;
  final String farmerName;
  final String village;
  final FieldTripCityRef? city;
  final String landAreaBigha;
  final List<CropModel> crops;
  final bool usesOurProducts;
  final List<FarmerVisitProductRef> products;
  final int visitCount;
  final String lastVisitedAt;
  final List<FieldTripPersonRef> salesPeople;
  final List<FarmerVisitSummary> visits;

  const FarmerModel({
    required this.contactNumber,
    this.farmerName = '',
    this.village = '',
    this.city,
    this.landAreaBigha = '',
    this.crops = const [],
    this.usesOurProducts = false,
    this.products = const [],
    this.visitCount = 0,
    this.lastVisitedAt = '',
    this.salesPeople = const [],
    this.visits = const [],
  });

  factory FarmerModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];

    return FarmerModel(
      contactNumber: stringOf(json['contact_number']),
      farmerName: stringOf(json['farmer_name']),
      village: stringOf(json['village']),
      city: city is Map
          ? FieldTripCityRef.fromJson(Map<String, dynamic>.from(city))
          : null,
      landAreaBigha: decimalOf(json['land_area_bigha']),
      crops: listOf(json['crops'], CropModel.fromJson),
      usesOurProducts: json['uses_our_products'] == true,
      products: listOf(json['products'], FarmerVisitProductRef.fromJson),
      visitCount: asInt(json['visit_count']),
      lastVisitedAt: stringOf(json['last_visited_at']),
      salesPeople: listOf(json['sales_people'], FieldTripPersonRef.fromJson),
      visits: listOf(json['visits'], FarmerVisitSummary.fromJson),
    );
  }

  String get cityName => city?.name ?? '';

  int? get cityId => city?.id;

  List<String> get cropNames => crops.map((crop) => crop.name).toList();

  List<String> get productNames =>
      products.map((product) => product.name).toList();

  List<String> get salesPeopleNames =>
      salesPeople.map((person) => person.name).toList();

  num? get landAreaValue => num.tryParse(landAreaBigha);

  DateTime? get lastVisitedDateTime => DateTime.tryParse(lastVisitedAt);

  static String stringOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }

  static String decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value.trim();
    return '$value';
  }

  static int asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static List<T> listOf<T>(
    dynamic value,
    T Function(Map<String, dynamic>) parser,
  ) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((entry) => parser(Map<String, dynamic>.from(entry)))
        .toList();
  }
}
