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

  /// Overrides the destination city the server would otherwise derive from
  /// the order's own delivery address. Omitted (null) when the admin leaves
  /// it as the order's own city -- only sent when they actually change it.
  final int? toCityId;
  final String driverName;
  final String driverNumber;
  final String vehicleNumber;
  final List<DispatchItemModel> items;

  const DispatchRequestModel({
    required this.fromCityId,
    this.toCityId,
    required this.driverName,
    required this.driverNumber,
    required this.vehicleNumber,
    this.items = const [],
  });

  Map<String, dynamic> toJson() => {
    'from_city_id': fromCityId,
    if (toCityId != null) 'to_city_id': toCityId,
    'driver_name': driverName,
    'driver_number': driverNumber,
    'vehicle_number': vehicleNumber,
    'items': items.map((item) => item.toJson()).toList(),
  };
}
