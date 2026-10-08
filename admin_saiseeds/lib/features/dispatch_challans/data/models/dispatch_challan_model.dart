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
  /// Not sent by the server -- kept as a client-side constant on request,
  /// since the backend's own copy of this was reverted. Update here if the
  /// real licence is renewed or changes.
  static const String SEEDS_LICENCE_NUMBER = '305 dt.02-07-2010';

  final String companyName;
  final String companyAddress;
  final String gstNumber;
  final String stateName;
  final String contactNumber;
  final String email;
  final String web;
  final String seedsLicenceNumber;

  const ChallanCompanyModel({
    this.companyName = '',
    this.companyAddress = '',
    this.gstNumber = '',
    this.stateName = '',
    this.contactNumber = '',
    this.email = '',
    this.web = '',
    this.seedsLicenceNumber = SEEDS_LICENCE_NUMBER,
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
      // The server no longer sends this (see SEEDS_LICENCE_NUMBER); fall
      // back to the hardcoded value whenever the key is absent or blank.
      seedsLicenceNumber: ('${json['seeds_licence_number'] ?? ''}').trim().isEmpty
          ? SEEDS_LICENCE_NUMBER
          : '${json['seeds_licence_number']}',
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

/// The "delivery to" party, when the order was booked for someone other than
/// the client themselves (e.g. the client's own sub-dealer). Null means the
/// goods go to the client's own address -- the consignee details already
/// carry everything a challan needs in that case.
class ChallanBookedForModel {
  final int id;
  final String partyName;
  final String villageName;
  final ChallanAddressModel? address;
  final String transportName;
  final String contactNumber;

  const ChallanBookedForModel({
    this.id = 0,
    this.partyName = '',
    this.villageName = '',
    this.address,
    this.transportName = '',
    this.contactNumber = '',
  });

  factory ChallanBookedForModel.fromJson(Map<String, dynamic> json) {
    final dynamic address = json['address'];

    return ChallanBookedForModel(
      id: _asInt(json['id']),
      partyName: json['party_name'] as String? ?? '',
      villageName: json['village_name'] as String? ?? '',
      address: address is Map
          ? ChallanAddressModel.fromJson(Map<String, dynamic>.from(address))
          : null,
      transportName: json['transport_name'] as String? ?? '',
      contactNumber: '${json['contact_number'] ?? ''}',
    );
  }

  String get addressLine => address?.singleLine ?? '';

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
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
  final String challanNumber;
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
    this.challanNumber = '',
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
      challanNumber: '${json['challan_number'] ?? ''}',
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

  /// Bags on this line, or 1 for a loose custom-order line which has none.
  int get effectiveBags => quantity <= 0 ? 1 : quantity;

  /// Packets actually shipped: packets per bag x bags.
  ///
  /// A custom order sells loose packets and sends no `quantity`, so the raw
  /// multiplication would zero the line out.
  int get shippedPackets => packets * effectiveBags;

  /// Whether this line came from a bagged order. A custom-order line has no
  /// bag count, so the Bags column has nothing to show for it.
  bool get hasBags => quantity > 0;

  /// Weight actually shipped: packet weight x packets x bags.
  ///
  /// Derived rather than read from `total_weight`, which a custom order's
  /// line omits and which counts one bag only where it is present.
  String get shippedWeight {
    final double? unit = double.tryParse(packetWeight.trim());
    if (unit == null) return '';
    final double total = unit * shippedPackets;
    return total.toStringAsFixed(3);
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
  final ChallanBookedForModel? bookedFor;
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
    this.bookedFor,
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
    final dynamic bookedFor = json['booked_for'];
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
      bookedFor: bookedFor is Map
          ? ChallanBookedForModel.fromJson(Map<String, dynamic>.from(bookedFor))
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

  String get challanNumber => dispatch?.challanNumber ?? '';

  /// What the saved PDF is named by: the challan number when the API has
  /// issued one, else the internal dispatch id.
  String get fileReference {
    final String number = challanNumber.trim();
    return number.isEmpty ? dispatchPublicId : number;
  }

  String get receiverName => receiver?.companyName ?? '';

  String get receiverGst => receiver?.gstNumber ?? '';

  String get receiverAddress => receiver?.address?.singleLine ?? '';

  String get contactSummary => receiver?.contactSummary ?? '';

  String get driverSummary => dispatch?.driverSummary ?? '';

  /// The "Delivery To" name shown on the challan: the booked-for party when
  /// the order was placed for someone else, else the consignee itself --
  /// never both, so this is always one name, never a second block.
  String get deliveryToName =>
      bookedFor != null ? bookedFor!.partyName : receiverName;

  String get deliveryToAddress =>
      bookedFor != null ? bookedFor!.addressLine : receiverAddress;

  String get deliveryToGst => bookedFor != null ? '' : receiverGst;

  /// "Name - Number" for whichever contact applies to the delivery-to party.
  String get deliveryToContact {
    if (bookedFor == null) return contactSummary;
    final String transport = bookedFor!.transportName.trim();
    final String number = bookedFor!.contactNumber.trim();
    if (transport.isEmpty) return number;
    if (number.isEmpty) return transport;
    return '$transport - $number';
  }

  /// The village the goods travel to -- the booked-for party's village when
  /// set, else the dispatch's own destination city as before.
  String get deliveryToPlace =>
      bookedFor != null ? bookedFor!.villageName : (dispatch?.toCity ?? '');

  /// "Parent (Child)" for a table row -- the client the order actually
  /// belongs to stays visible even once a delivery-to party replaces every
  /// other detail in the row, so the two are never confused for each other.
  /// The challan document itself keeps its own plain [deliveryToName]; this
  /// is for the list only.
  String get deliveryToTableName {
    if (bookedFor == null) return receiverName;
    final String parent = receiverName.trim();
    final String child = bookedFor!.partyName.trim();
    if (parent.isEmpty) return child;
    if (child.isEmpty) return parent;
    return '$parent ($child)';
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
