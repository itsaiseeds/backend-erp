class FieldTripsEndpoints {
  FieldTripsEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/field-trips/';

  static String detail(String publicId) => '$_base/field-trip/$publicId';

  static String edit(String publicId) => '$_base/edit-field-trip/$publicId';

  static String approve(String publicId) =>
      '$_base/approve-field-trip/$publicId';

  static String unapprove(String publicId) =>
      '$_base/unapprove-field-trip/$publicId';

  static String farmerVisits(String publicId) =>
      '$_base/field-trip-farmer-visits/$publicId';

  static const String farmers = '$_base/farmers';
}
