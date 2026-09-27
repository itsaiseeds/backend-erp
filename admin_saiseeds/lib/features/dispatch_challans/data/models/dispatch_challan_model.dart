import '../../../../core/constants/app_strings.dart';
class ChallanAddressModel {
  final String line1;
  final String line2;
  final String pincode;
  final String city;
  final String state;
  final String country;
  final int? cityId;

  const ChallanAddressModel({
    this.line1 = '',
    this.line2 = '',
    this.pincode = '',
    this.city = '',
    this.state = '',
    this.country = '',
    this.cityId,
  });

  factory ChallanAddressModel.fromJson(Map<String, dynamic> json) {
    return ChallanAddressModel(
      line1: json['line_1'] as String? ?? '',
      line2: json['line_2'] as String? ?? '',
      pincode: '${json['pincode'] ?? ''}',
      city: json['city'] as String? ?? '',
      state: json['state'] as String? ?? '',
      country: json['country'] as String? ?? '',
      cityId: _asNullableInt(json['city_id']),
    );
  }

  /// One comma-separated line, skipping the parts the server left blank.
  String get singleLine => [
    line1,
    line2,
    city,
    state,
    pincode,
    country,
  ].map((part) => part.trim()).where((part) => part.isNotEmpty).join(', ');

  static int? _asNullableInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value');
  }
}

class ChallanCompanyModel {
  final String companyName;
  final String companyAddress;
  final String gstNumber;
  final String stateName;
  final String contactNumber;
  final String email;
  final String web;

  const ChallanCompanyModel({
    this.companyName = '',
    this.companyAddress = '',
    this.gstNumber = '',
    this.stateName = '',
    this.contactNumber = '',
    this.email = '',
    this.web = '',
  });

  factory ChallanCompanyModel.fromJson(Map<String, dynamic> json) {
    return ChallanCompanyModel(
      companyName: json['company_name'] as String? ?? '',
      companyAddress: json['company_address'] as String? ?? '',
      gstNumber: '${json['gst_number'] ?? ''}',
      stateName: json['state_name'] as String? ?? '',
      contactNumber: '${json['contact_number'] ?? ''}',
      email: json['email'] as String? ?? '',
      web: json['web'] as String? ?? '',
    );
  }
}

class ChallanReceiverModel {
  final String companyName;
  final String gstNumber;
  final ChallanAddressModel? address;
  final String contactPersonName;
  final String contactPersonNumber;

  const ChallanReceiverModel({
    this.companyName = '',
    this.gstNumber = '',
    this.address,
    this.contactPersonName = '',
    this.contactPersonNumber = '',
  });

  factory ChallanReceiverModel.fromJson(Map<String, dynamic> json) {
    final dynamic address = json['address'];

    return ChallanReceiverModel(
      companyName: json['company_name'] as String? ?? '',
      gstNumber: '${json['gst_number'] ?? ''}',
      address: address is Map
          ? ChallanAddressModel.fromJson(Map<String, dynamic>.from(address))
          : null,
      contactPersonName: json['contact_person_name'] as String? ?? '',
      contactPersonNumber: '${json['contact_person_number'] ?? ''}',
    );
  }

  /// "Name - Number", collapsing to whichever half exists.
  String get contactSummary {
    final String name = contactPersonName.trim();
    final String number = contactPersonNumber.trim();
    if (name.isEmpty) return number;
    if (number.isEmpty) return name;
    return '$name - $number';
  }
}

class ChallanAgencyRef {
  final int id;
  final String name;

  const ChallanAgencyRef({required this.id, this.name = ''});

  factory ChallanAgencyRef.fromJson(Map<String, dynamic> json) {
    return ChallanAgencyRef(
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

class ChallanDispatchModel {
  final String publicId;
  final String lrNumber;
  final String dispatchDate;
  final bool isPrivate;
  final String vehicleNumber;
  final String driverName;
  final String driverNumber;
  final String fromCity;
  final String toCity;
  final ChallanAgencyRef? transportAgency;

  const ChallanDispatchModel({
    this.publicId = '',
    this.lrNumber = '',
    this.dispatchDate = '',
    this.isPrivate = false,
    this.vehicleNumber = '',
    this.driverName = '',
    this.driverNumber = '',
    this.fromCity = '',
    this.toCity = '',
    this.transportAgency,
  });

  factory ChallanDispatchModel.fromJson(Map<String, dynamic> json) {
    final dynamic agency = json['transport_agency'];

    return ChallanDispatchModel(
      publicId: '${json['public_id'] ?? ''}',
      lrNumber: '${json['lr_number'] ?? ''}',
      dispatchDate: '${json['dispatch_date'] ?? ''}',
      isPrivate: json['is_private'] == true,
      vehicleNumber: '${json['vehicle_number'] ?? ''}',
      driverName: json['driver_name'] as String? ?? '',
      driverNumber: '${json['driver_number'] ?? ''}',
      fromCity: json['from_city'] as String? ?? '',
      toCity: json['to_city'] as String? ?? '',
      transportAgency: agency is Map
          ? ChallanAgencyRef.fromJson(Map<String, dynamic>.from(agency))
          : null,
    );
  }

  DateTime? get dispatchDateTime => DateTime.tryParse(dispatchDate);

  /// "Private" for an own vehicle, otherwise the agency's name.
  String get transportLabel {
    if (isPrivate) return AppStrings.TRANSPORT_PRIVATE;
    final String name = transportAgency?.name.trim() ?? '';
    return name.isEmpty ? AppStrings.TRANSPORT_AGENCY : name;
  }

  String get driverSummary {
    final String name = driverName.trim();
    final String number = driverNumber.trim();
    if (name.isEmpty) return number;
    if (number.isEmpty) return name;
    return '$name - $number';
  }
}

class ChallanItemModel {
  final String publicId;
  final String productName;
  final String packetWeight;
  final int packets;
  final String totalWeight;
  final String sellingPrice;
  final String lotNumber;
  final int quantity;
  final String negotiatedSellingPrice;
  final String lineTotal;

  const ChallanItemModel({
    this.publicId = '',
    this.productName = '',
    this.packetWeight = '',
    this.packets = 0,
    this.totalWeight = '',
    this.sellingPrice = '',
    this.lotNumber = '',
    this.quantity = 0,
    this.negotiatedSellingPrice = '',
    this.lineTotal = '',
  });

  factory ChallanItemModel.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];

    return ChallanItemModel(
      publicId: '${json['public_id'] ?? ''}',
      productName: product is Map ? '${product['name'] ?? ''}' : '',
      packetWeight: _decimalOf(json['packet_weight']),
      packets: _asInt(json['packets']),
      totalWeight: _decimalOf(json['total_weight']),
      sellingPrice: _decimalOf(json['selling_price']),
      lotNumber: '${json['lot_number'] ?? ''}',
      quantity: _asInt(json['quantity']),
      negotiatedSellingPrice: _decimalOf(json['negotiated_selling_price']),
      lineTotal: _decimalOf(json['line_total']),
    );
  }

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}

class DispatchChallanModel {
  final String orderPublicId;
  final ChallanCompanyModel? ourDetails;
  final ChallanReceiverModel? receiver;
  final String hsnCode;
  final String financialYear;
  final ChallanDispatchModel? dispatch;
  final List<ChallanItemModel> items;
  final int itemCount;
  final String totalAmount;
  final int totalPackets;

  const DispatchChallanModel({
    this.orderPublicId = '',
    this.ourDetails,
    this.receiver,
    this.hsnCode = '',
    this.financialYear = '',
    this.dispatch,
    this.items = const [],
    this.itemCount = 0,
    this.totalAmount = '',
    this.totalPackets = 0,
  });

  factory DispatchChallanModel.fromJson(Map<String, dynamic> json) {
    final dynamic ourDetails = json['our_details'];
    final dynamic receiver = json['receiver_details'];
    final dynamic dispatch = json['dispatch'];
    final dynamic items = json['items'];

    return DispatchChallanModel(
      orderPublicId: '${json['order_public_id'] ?? ''}',
      ourDetails: ourDetails is Map
          ? ChallanCompanyModel.fromJson(Map<String, dynamic>.from(ourDetails))
          : null,
      receiver: receiver is Map
          ? ChallanReceiverModel.fromJson(Map<String, dynamic>.from(receiver))
          : null,
      hsnCode: '${json['hsn_code'] ?? ''}',
      financialYear: '${json['financial_year'] ?? ''}',
      dispatch: dispatch is Map
          ? ChallanDispatchModel.fromJson(Map<String, dynamic>.from(dispatch))
          : null,
      items: items is List
          ? items
                .whereType<Map>()
                .map(
                  (item) => ChallanItemModel.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList()
          : const [],
      itemCount: _asInt(json['item_count']),
      totalAmount: _decimalOf(json['total_amount']),
      totalPackets: _asInt(json['total_packets']),
    );
  }

  String get dispatchPublicId => dispatch?.publicId ?? '';

  String get receiverName => receiver?.companyName ?? '';

  String get receiverGst => receiver?.gstNumber ?? '';

  String get receiverAddress => receiver?.address?.singleLine ?? '';

  String get contactSummary => receiver?.contactSummary ?? '';

  String get driverSummary => dispatch?.driverSummary ?? '';

  static String _decimalOf(dynamic value) {
    if (value == null) return '';
    if (value is String) return value;
    return '$value';
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
