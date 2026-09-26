class RawMaterialsEndpoints {
  RawMaterialsEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String inwardList = '$_base/inward-raw-materials';
  static const String inwardCreate = '$_base/inward-raw-materials';

  static String inwardDetail(String publicId) =>
      '$_base/inward-raw-material/$publicId';

  static const String otherMaterialTypes = '$_base/other-material-types';

  static const String recipesList = '$_base/other-material-recipes';
  static const String recipesCreate = '$_base/other-material-recipes';

  static String recipeDetail(String publicId) =>
      '$_base/other-material-recipe/$publicId';

  static const String otherInwardList = '$_base/inward-other-materials';
  static const String otherInwardCreate = '$_base/inward-other-materials';

  static String otherInwardDetail(String publicId) =>
      '$_base/inward-other-material/$publicId';
}
