import '../models/crop_model.dart';
import '../network/api_client.dart';
import '../../features/products/data/crops_repository.dart';

class CropsService {
  CropsService._();

  static final CropsService instance = CropsService._();

  CropsRepository? _repository;
  final List<CropModel> _crops = [];
  bool _isLoaded = false;

  set repository(CropsRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<CropModel> get crops => List.unmodifiable(_crops);

  CropsRepository get _resolvedRepository =>
      _repository ??= CropsRepository(apiClient: ApiClient());

  Future<bool> loadCrops({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      final List<CropModel> fetched = await _resolvedRepository.fetchCrops();
      _crops
        ..clear()
        ..addAll(fetched);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<CropModel> createCrop(String name) async {
    final CropModel created = await _resolvedRepository.createCrop(name);
    _crops.removeWhere((crop) => crop.id == created.id);
    _crops.add(created);
    _isLoaded = true;
    return created;
  }

  void reset() {
    _crops.clear();
    _isLoaded = false;
    _repository = null;
  }
}
