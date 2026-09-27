import '../network/api_client.dart';
import '../../features/product_packagings/data/models/product_packaging_model.dart';
import '../../features/product_packagings/data/product_packagings_repository.dart';

class PackagingsService {
  PackagingsService._();

  static final PackagingsService instance = PackagingsService._();

  ProductPackagingsRepository? _repository;
  final List<ProductPackagingModel> _packagings = [];
  bool _isLoaded = false;

  set repository(ProductPackagingsRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<ProductPackagingModel> get packagings => List.unmodifiable(_packagings);

  ProductPackagingsRepository get _resolvedRepository =>
      _repository ??= ProductPackagingsRepository(apiClient: ApiClient());

  ProductPackagingModel? packagingByPublicId(String publicId) {
    for (final ProductPackagingModel packaging in _packagings) {
      if (packaging.publicId == publicId) return packaging;
    }
    return null;
  }

  Future<bool> loadPackagings({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      final List<ProductPackagingModel> fetched = await _resolvedRepository
          .fetchProductPackagings();
      _packagings
        ..clear()
        ..addAll(fetched);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _packagings.clear();
    _isLoaded = false;
    _repository = null;
  }
}
