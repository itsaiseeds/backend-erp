import '../network/api_client.dart';
import '../../features/other_raw_materials/data/models/other_material_type_model.dart';
import '../../features/other_raw_materials/data/other_raw_materials_repository.dart';

class MaterialTypesService {
  MaterialTypesService._();

  static final MaterialTypesService instance = MaterialTypesService._();

  OtherRawMaterialsRepository? _repository;
  final List<OtherMaterialTypeModel> _types = [];
  bool _isLoaded = false;

  set repository(OtherRawMaterialsRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<OtherMaterialTypeModel> get types => List.unmodifiable(_types);

  OtherRawMaterialsRepository get _resolvedRepository =>
      _repository ??= OtherRawMaterialsRepository(apiClient: ApiClient());

  OtherMaterialTypeModel? typeById(int? id) {
    if (id == null) return null;
    for (final OtherMaterialTypeModel type in _types) {
      if (type.id == id) return type;
    }
    return null;
  }

  Future<bool> loadMaterialTypes({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      final List<OtherMaterialTypeModel> fetched = await _resolvedRepository
          .fetchMaterialTypes();
      _types
        ..clear()
        ..addAll(fetched);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _types.clear();
    _isLoaded = false;
    _repository = null;
  }
}
