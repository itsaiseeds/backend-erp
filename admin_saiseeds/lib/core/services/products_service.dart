import '../network/api_client.dart';
import '../../features/products/data/models/product_model.dart';
import '../../features/products/data/products_repository.dart';

class ProductsService {
  ProductsService._();

  static final ProductsService instance = ProductsService._();

  ProductsRepository? _repository;
  final List<ProductModel> _products = [];
  bool _isLoaded = false;

  set repository(ProductsRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<ProductModel> get products => List.unmodifiable(_products);

  ProductsRepository get _resolvedRepository =>
      _repository ??= ProductsRepository(apiClient: ApiClient());

  ProductModel? productByPublicId(String publicId) {
    for (final ProductModel product in _products) {
      if (product.publicId == publicId) return product;
    }
    return null;
  }

  Future<bool> loadProducts({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      final List<ProductModel> fetched = await _resolvedRepository
          .fetchProducts();
      _products
        ..clear()
        ..addAll(fetched);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _products.clear();
    _isLoaded = false;
    _repository = null;
  }
}
