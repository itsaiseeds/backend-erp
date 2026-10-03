import '../network/api_client.dart';
import '../../features/other_raw_materials/data/models/other_material_recipe_model.dart';
import '../../features/other_raw_materials/data/models/paginated_other_material_recipes_model.dart';
import '../../features/other_raw_materials/data/other_raw_materials_repository.dart';

class RecipesService {
  RecipesService._();

  static final RecipesService instance = RecipesService._();


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
      // One call with all=true instead of walking pages: the endpoint
      // returns every row, so nothing is missed and nothing is capped.
      final PaginatedOtherMaterialRecipesModel result =
          await _resolvedRepository.fetchRecipes(
            queryParams: const {'all': true},
          );
      final List<OtherMaterialRecipeModel> collected = result.results;

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
