class DispatchItemModel {
  final String productPackagingPublicId;
  final String lotNumber;

  const DispatchItemModel({
    required this.productPackagingPublicId,
    this.lotNumber = '',
  });

  Map<String, dynamic> toJson() => {
    'product_packaging_public_id': productPackagingPublicId,
    'lot_number': lotNumber,
  };
}

class DispatchRequestModel {
  final int fromCityId;

  /// The challan's "To". Blank is valid -- the server then defaults it from
  /// the booked-for address, else the delivery address.
  final String deliveryTo;
  final String driverName;
  final String driverNumber;
  final String vehicleNumber;
  final List<DispatchItemModel> items;

  const DispatchRequestModel({
    required this.fromCityId,
    this.deliveryTo = '',
    required this.driverName,
    required this.driverNumber,
    required this.vehicleNumber,
    this.items = const [],
  });

  Map<String, dynamic> toJson() => {
    'from_city_id': fromCityId,
    'delivery_to': deliveryTo,
    'driver_name': driverName,
    'driver_number': driverNumber,
    'vehicle_number': vehicleNumber,
    'items': items.map((item) => item.toJson()).toList(),
  };
}
