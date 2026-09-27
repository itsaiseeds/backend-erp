import '../network/api_client.dart';
import '../../features/other_raw_materials/data/models/other_material_recipe_model.dart';
import '../../features/other_raw_materials/data/models/paginated_other_material_recipes_model.dart';
import '../../features/other_raw_materials/data/other_raw_materials_repository.dart';

class RecipesService {
  RecipesService._();

  static final RecipesService instance = RecipesService._();

  static const int _PAGE_SIZE = 30;
  static const int _MAX_PAGES = 40;

  OtherRawMaterialsRepository? _repository;
  final List<OtherMaterialRecipeModel> _recipes = [];
  bool _isLoaded = false;

  set repository(OtherRawMaterialsRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<OtherMaterialRecipeModel> get recipes => List.unmodifiable(_recipes);

  OtherRawMaterialsRepository get _resolvedRepository =>
      _repository ??= OtherRawMaterialsRepository(apiClient: ApiClient());

  OtherMaterialRecipeModel? recipeByPublicId(String publicId) {
    for (final OtherMaterialRecipeModel recipe in _recipes) {
      if (recipe.publicId == publicId) return recipe;
    }
    return null;
  }

  Future<bool> loadRecipes({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      final List<OtherMaterialRecipeModel> collected = [];

      for (int page = 1; page <= _MAX_PAGES; page++) {
        final PaginatedOtherMaterialRecipesModel result =
            await _resolvedRepository.fetchRecipes(
              queryParams: {'page': page, 'page_size': _PAGE_SIZE},
            );

        collected.addAll(result.results);

        final int? next = result.nextPageNumber;
        if (next == null || next <= page || result.results.isEmpty) break;
      }

      _recipes
        ..clear()
        ..addAll(collected);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _recipes.clear();
    _isLoaded = false;
    _repository = null;
  }
}
