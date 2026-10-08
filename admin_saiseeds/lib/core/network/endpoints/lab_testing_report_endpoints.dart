class LabTestingReportEndpoints {
  LabTestingReportEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/lab-testings';

  static String detail(String publicId) => '$_base/lab-testing/$publicId';
}
