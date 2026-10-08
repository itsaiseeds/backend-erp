import '../../../../core/models/created_by_model.dart';

/// `{public_id, name}` -- the product a tested lot belongs to.
class LabTestingProductRef {
  final String publicId;
  final String name;

  const LabTestingProductRef({this.publicId = '', this.name = ''});

  factory LabTestingProductRef.fromJson(Map<String, dynamic> json) {
    return LabTestingProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

/// The tested lot, nested inside a [LabTestingReportModel].
class LabTestingLotRef {
  final String publicId;
  final LabTestingProductRef? product;
  final CreatedByModel? party;
  final String lotNo;
  final String quantityKg;
  final String status;

  const LabTestingLotRef({
    this.publicId = '',
    this.product,
    this.party,
    this.lotNo = '',
    this.quantityKg = '',
    this.status = '',
  });

  factory LabTestingLotRef.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final dynamic party = json['party'];

    return LabTestingLotRef(
      publicId: '${json['public_id'] ?? ''}',
      product: product is Map
          ? LabTestingProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      party: party is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(party))
          : null,
      lotNo: '${json['lot_no'] ?? ''}',
      quantityKg: _textOf(json['quantity_kg']),
      status: json['status'] as String? ?? '',
    );
  }

  String get productName => product?.name ?? '';

  String get partyName => party?.name ?? '';

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }
}

/// One completed lab test (`LT-…`), view-only: entered and edited by the lab
/// tester's own app, never from here.
class LabTestingReportModel {
  final String publicId;
  final int numberOfPlants;
  final int femaleCount;
  final int otCount;
  final String geneticalImpurity;
  final String growOutTest;
  final String result;
  final String comment;
  final CreatedByModel? testedBy;
  final String testedAt;
  final LabTestingLotRef? inwardRawMaterial;

  const LabTestingReportModel({
    required this.publicId,
    this.numberOfPlants = 0,
    this.femaleCount = 0,
    this.otCount = 0,
    this.geneticalImpurity = '',
    this.growOutTest = '',
    this.result = '',
    this.comment = '',
    this.testedBy,
    this.testedAt = '',
    this.inwardRawMaterial,
  });

  factory LabTestingReportModel.fromJson(Map<String, dynamic> json) {
    final dynamic testedBy = json['tested_by'];
    final dynamic lot = json['inward_raw_material'];

    return LabTestingReportModel(
      publicId: '${json['public_id'] ?? ''}',
      numberOfPlants: _asInt(json['number_of_plants']),
      femaleCount: _asInt(json['female_count']),
      otCount: _asInt(json['ot_count']),
      geneticalImpurity: _textOf(json['genetical_impurity']),
      growOutTest: _textOf(json['grow_out_test']),
      result: json['result'] as String? ?? '',
      comment: json['comment'] as String? ?? '',
      testedBy: testedBy is Map
          ? CreatedByModel.fromJson(Map<String, dynamic>.from(testedBy))
          : null,
      testedAt: _textOf(json['tested_at']),
      inwardRawMaterial: lot is Map
          ? LabTestingLotRef.fromJson(Map<String, dynamic>.from(lot))
          : null,
    );
  }

  String get testedByName => testedBy?.name ?? '';

  String get productName => inwardRawMaterial?.productName ?? '';

  String get partyName => inwardRawMaterial?.partyName ?? '';

  String get lotNo => inwardRawMaterial?.lotNo ?? '';

  bool get isPass => result.toLowerCase() == 'pass';

  bool get isFail => result.toLowerCase() == 'fail';

  bool matchesSearch(String query) {
    final String needle = query.trim().toLowerCase();
    if (needle.isEmpty) return true;
    return publicId.toLowerCase().contains(needle) ||
        productName.toLowerCase().contains(needle) ||
        partyName.toLowerCase().contains(needle) ||
        lotNo.toLowerCase().contains(needle) ||
        testedByName.toLowerCase().contains(needle);
  }

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
