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
  final String driverName;
  final String driverNumber;
  final String vehicleNumber;
  final List<DispatchItemModel> items;

  const DispatchRequestModel({
    required this.fromCityId,
    required this.driverName,
    required this.driverNumber,
    required this.vehicleNumber,
    this.items = const [],
  });

  Map<String, dynamic> toJson() => {
    'from_city_id': fromCityId,
    'driver_name': driverName,
    'driver_number': driverNumber,
    'vehicle_number': vehicleNumber,
    'items': items.map((item) => item.toJson()).toList(),
  };
}
