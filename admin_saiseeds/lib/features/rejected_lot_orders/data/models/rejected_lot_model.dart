class RejectedLotPartyRef {
  final int id;
  final String name;

  const RejectedLotPartyRef({this.id = 0, this.name = ''});

  factory RejectedLotPartyRef.fromJson(Map<String, dynamic> json) {
    return RejectedLotPartyRef(
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

class RejectedLotProductRef {
  final String publicId;
  final String name;

  const RejectedLotProductRef({this.publicId = '', this.name = ''});

  factory RejectedLotProductRef.fromJson(Map<String, dynamic> json) {
    return RejectedLotProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: json['name'] as String? ?? '',
    );
  }
}

class RejectedLotLabTestRef {
  final String publicId;
  final String? result;
  final String comment;
  final String? testedAt;

  const RejectedLotLabTestRef({
    this.publicId = '',
    this.result,
    this.comment = '',
    this.testedAt,
  });

  factory RejectedLotLabTestRef.fromJson(Map<String, dynamic> json) {
    return RejectedLotLabTestRef(
      publicId: '${json['public_id'] ?? ''}',
      result: json['result'] as String?,
      comment: json['comment'] as String? ?? '',
      testedAt: json['tested_at'] as String?,
    );
  }
}

/// A rejected raw-material lot that still has stock free to sell, as the
/// farmer's-lot picker (step 2 of the rejected-order wizard) lists it.
class RejectedLotModel {
  final String inwardRawMaterialPublicId;
  final RejectedLotPartyRef? party;
  final String farmerName;
  final RejectedLotProductRef? product;
  final String lotNo;
  final String quantityKg;
  final String bookedKg;
  final String remainingKg;
  final String inwardDate;
  final String rejectedOn;
  final String? labSamplingDate;
  final RejectedLotLabTestRef? labTest;

  const RejectedLotModel({
    this.inwardRawMaterialPublicId = '',
    this.party,
    this.farmerName = '',
    this.product,
    this.lotNo = '',
    this.quantityKg = '',
    this.bookedKg = '',
    this.remainingKg = '',
    this.inwardDate = '',
    this.rejectedOn = '',
    this.labSamplingDate,
    this.labTest,
  });

  factory RejectedLotModel.fromJson(Map<String, dynamic> json) {
    final dynamic party = json['party'];
    final dynamic product = json['product'];
    final dynamic labTest = json['lab_test'];

    return RejectedLotModel(
      inwardRawMaterialPublicId: '${json['inward_raw_material_public_id'] ?? ''}',
      party: party is Map
          ? RejectedLotPartyRef.fromJson(Map<String, dynamic>.from(party))
          : null,
      farmerName: json['farmer_name'] as String? ?? '',
      product: product is Map
          ? RejectedLotProductRef.fromJson(Map<String, dynamic>.from(product))
          : null,
      lotNo: json['lot_no'] as String? ?? '',
      quantityKg: _decimalOf(json['quantity_kg']),
      bookedKg: _decimalOf(json['booked_kg']),
      remainingKg: _decimalOf(json['remaining_kg']),
      inwardDate: '${json['inward_date'] ?? ''}',
      rejectedOn: '${json['rejected_on'] ?? ''}',
      labSamplingDate: json['lab_sampling_date'] as String?,
      labTest: labTest is Map
          ? RejectedLotLabTestRef.fromJson(Map<String, dynamic>.from(labTest))
          : null,
    );
  }

  String get productName => product?.name ?? '';

  String get productPublicId => product?.publicId ?? '';

  num get remainingKgValue => num.tryParse(remainingKg) ?? 0;

  bool get hasStockLeft => remainingKgValue > 0;

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }
}
