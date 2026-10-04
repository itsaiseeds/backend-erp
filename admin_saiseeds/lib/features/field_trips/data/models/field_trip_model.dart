class FieldTripCityRef {
  final int id;
  final String name;

  const FieldTripCityRef({required this.id, required this.name});

  factory FieldTripCityRef.fromJson(Map<String, dynamic> json) {
    return FieldTripCityRef(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class FieldTripPersonRef {
  final int id;
  final String name;
  final String phoneNumber;

  const FieldTripPersonRef({
    required this.id,
    required this.name,
    this.phoneNumber = '',
  });

  factory FieldTripPersonRef.fromJson(Map<String, dynamic> json) {
    return FieldTripPersonRef(
      id: _asInt(json['id']),
      name: json['name'] as String? ?? '',
      phoneNumber: '${json['phone_number'] ?? ''}',
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class FieldTripStatus {
  FieldTripStatus._();

  static const String PLANNED = 'planned';
  static const String APPROVED = 'approved';
  static const String IN_PROGRESS = 'in_progress';
  static const String COMPLETED = 'completed';

  /// The keys above match the normalised payload status; the API's own filter
  /// options are the uppercase codes, so the chip value is spelled separately.
  static const String PLANNED_CODE = 'PLANNED';
}

class FieldTripModel {
  final String publicId;
  final String status;
  final FieldTripCityRef? city;
  final String village;
  final String expectedStartAt;
  final String expectedEndAt;
  final String startedAt;
  final String endedAt;
  final FieldTripPersonRef? salesPerson;
  final FieldTripPersonRef? approvedBy;
  final String approvedAt;
  final int farmerVisitCount;
  final String createdAt;

  const FieldTripModel({
    required this.publicId,
    this.status = '',
    this.city,
    this.village = '',
    this.expectedStartAt = '',
    this.expectedEndAt = '',
    this.startedAt = '',
    this.endedAt = '',
    this.salesPerson,
    this.approvedBy,
    this.approvedAt = '',
    this.farmerVisitCount = 0,
    this.createdAt = '',
  });

  factory FieldTripModel.fromJson(Map<String, dynamic> json) {
    final dynamic city = json['city'];
    final dynamic salesPerson = json['sales_person'];
    final dynamic approvedBy = json['approved_by'];

    return FieldTripModel(
      publicId: '${json['public_id'] ?? ''}',
      status: '${json['status'] ?? ''}',
      city: city is Map
          ? FieldTripCityRef.fromJson(Map<String, dynamic>.from(city))
          : null,
      village: '${json['village'] ?? ''}',
      expectedStartAt: _stringOf(json['expected_start_at']),
      expectedEndAt: _stringOf(json['expected_end_at']),
      startedAt: _stringOf(json['started_at']),
      endedAt: _stringOf(json['ended_at']),
      salesPerson: salesPerson is Map
          ? FieldTripPersonRef.fromJson(
              Map<String, dynamic>.from(salesPerson),
            )
          : null,
      approvedBy: approvedBy is Map
          ? FieldTripPersonRef.fromJson(Map<String, dynamic>.from(approvedBy))
          : null,
      approvedAt: _stringOf(json['approved_at']),
      farmerVisitCount: _asInt(json['farmer_visit_count']),
      createdAt: _stringOf(json['created_at']),
    );
  }

  String get cityName => city?.name ?? '';

  int? get cityId => city?.id;

  String get salesPersonName => salesPerson?.name ?? '';

  String get salesPersonPhone => salesPerson?.phoneNumber ?? '';

  String get approverName => approvedBy?.name ?? '';

  String get _statusKey =>
      status.trim().toLowerCase().replaceAll(RegExp(r'[\s-]+'), '_');

  bool get isPlanned => _statusKey == FieldTripStatus.PLANNED;

  bool get isApproved => _statusKey == FieldTripStatus.APPROVED;

  bool get isInProgress => _statusKey == FieldTripStatus.IN_PROGRESS;

  bool get isCompleted => _statusKey == FieldTripStatus.COMPLETED;

  /// The admin owns approval only. Once a salesperson has started the trip
  /// nothing on this side may change it, so every gate below closes.
  bool get canApprove => isPlanned;

  bool get canUnapprove => isApproved;

  bool get canEdit => isPlanned;

  bool get canDelete => isPlanned || isApproved;

  String get statusLabel {
    final String raw = status.trim();
    if (raw.isEmpty) return '';
    if (!raw.contains('_')) return raw;
    return raw
        .split('_')
        .where((word) => word.isNotEmpty)
        .map((word) => '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  DateTime? get expectedStartDateTime => DateTime.tryParse(expectedStartAt);

  DateTime? get expectedEndDateTime => DateTime.tryParse(expectedEndAt);

  DateTime? get startedDateTime => DateTime.tryParse(startedAt);

  DateTime? get endedDateTime => DateTime.tryParse(endedAt);

  DateTime? get approvedDateTime => DateTime.tryParse(approvedAt);

  DateTime? get createdDateTime => DateTime.tryParse(createdAt);

  static String _stringOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}
