class InwardProductRef {
  final String publicId;
  final String name;

  const InwardProductRef({required this.publicId, required this.name});

  factory InwardProductRef.fromJson(Map<String, dynamic> json) {
    return InwardProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class InwardPartyRef {
  final int id;
  final String name;

  const InwardPartyRef({required this.id, required this.name});

  factory InwardPartyRef.fromJson(Map<String, dynamic> json) {
    return InwardPartyRef(
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

class InwardStatus {
  InwardStatus._();

  static const String LAB_TESTING = 'lab_testing';
  static const String IN_USE = 'in_use';
}

class InwardRawMaterialModel {
  final String publicId;
  final InwardProductRef? product;
  final InwardPartyRef? party;
  final String quantityKg;
  final String status;
  final String labSamplingDate;
  final String effectiveDate;

  const InwardRawMaterialModel({
    required this.publicId,
    this.product,
    this.party,
    this.quantityKg = '',
    this.status = '',
    this.labSamplingDate = '',
    this.effectiveDate = '',
  });

  factory InwardRawMaterialModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final dynamic party = json['party'];

    return InwardRawMaterialModel(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? InwardProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      party: party is Map
          ? InwardPartyRef.fromJson(Map<String, dynamic>.from(party))
          : null,
      quantityKg: _decimalOf(json['quantity_kg']),
      status: '${json['status'] ?? ''}',
      labSamplingDate: _dateOf(json['lab_sampling_date']),
      effectiveDate: _dateOf(json['effective_date']),
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  String get partyName => party?.name ?? '';

  int? get partyId => party?.id;

  String get _statusKey =>
      status.trim().toLowerCase().replaceAll(RegExp(r'[\s-]+'), '_');

  bool get isInUse => _statusKey == InwardStatus.IN_USE;

  String get statusLabel {
    final String raw = status.trim();
    if (raw.isEmpty) return '';
    if (raw.contains('_')) {
      return raw
          .split('_')
          .where((word) => word.isNotEmpty)
          .map((word) => '${word[0].toUpperCase()}${word.substring(1)}')
          .join(' ');
    }
    return raw;
  }

  num? get quantityValue => num.tryParse(quantityKg);

  DateTime? get labSamplingDateTime => DateTime.tryParse(labSamplingDate);

  DateTime? get effectiveDateTime => DateTime.tryParse(effectiveDate);

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static String _dateOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }
}
