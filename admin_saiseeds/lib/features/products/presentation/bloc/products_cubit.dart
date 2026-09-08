import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/product_model.dart';
import '../../data/products_repository.dart';

enum ProductsStatus { initial, loading, loaded, failure }

class ProductsState extends Equatable {
  final ProductsStatus status;
  final List<ProductModel> allProducts;
  final List<ProductModel> visibleProducts;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final bool isMutating;
  final String? errorMessage;

  const ProductsState({
    this.status = ProductsStatus.initial,
    this.allProducts = const [],
    this.visibleProducts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.limit = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.isMutating = false,
    this.errorMessage,
  });

  bool get isEmptySource =>
      status == ProductsStatus.loaded && allProducts.isEmpty;

  ProductsState copyWith({
    ProductsStatus? status,
    List<ProductModel>? allProducts,
    List<ProductModel>? visibleProducts,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return ProductsState(
      status: status ?? this.status,
      allProducts: allProducts ?? this.allProducts,
      visibleProducts: visibleProducts ?? this.visibleProducts,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      limit: limit ?? this.limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? this.filters,
      isMutating: isMutating ?? this.isMutating,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
    status,
    allProducts,
    visibleProducts,
    currentPage,
    totalPages,
    totalItems,
    limit,
    search,
    sortBy,
    sortOrder,
    filters,
    isMutating,
    errorMessage,
  ];
}

class ProductsCubit extends SafeCubit<ProductsState> {
  final ProductsRepository _repository;

  ProductsCubit({required ProductsRepository repository})
    : _repository = repository,
      super(const ProductsState());

  Future<void> loadProducts() async {
    emit(state.copyWith(status: ProductsStatus.loading, clearError: true));

    try {
      final List<ProductModel> products = await _repository.fetchProducts();
      emit(
        _projected(
          state.copyWith(
            status: ProductsStatus.loaded,
            allProducts: products,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: ProductsStatus.failure,
          errorMessage: _messageOf(error),
        ),
      );
    }
  }

  void applyQuery({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    final ProductsState next = ProductsState(
      status: state.status,
      allProducts: state.allProducts,
      visibleProducts: state.visibleProducts,
      currentPage: state.currentPage,
      totalPages: state.totalPages,
      totalItems: state.totalItems,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? const {},
      isMutating: state.isMutating,
      errorMessage: state.errorMessage,
    );

    emit(_projected(next, page: page));
  }

  Future<bool> createProduct({
    required String name,
    required int cropId,
    required String buyingPrice,
    required String sellingPrice,
  }) {
    return _mutate(
      () => _repository.createProduct(
        name: name,
        cropId: cropId,
        buyingPrice: buyingPrice,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<bool> updateProduct({
    required String publicId,
    required String name,
    required int cropId,
    required String buyingPrice,
    required String sellingPrice,
  }) {
    return _mutate(
      () => _repository.updateProduct(
        publicId: publicId,
        name: name,
        cropId: cropId,
        buyingPrice: buyingPrice,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<bool> deleteProduct(String publicId) =>
      _mutate(() => _repository.deleteProduct(publicId));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadProducts();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  ProductsState _projected(ProductsState source, {required int page}) {
    final List<ProductModel> searched = ListQuery.search<ProductModel>(
      source: source.allProducts,
      query: source.search,
      searchableValues: (product) => [
        product.name,
        product.cropName,
        product.buyingPrice,
        product.sellingPrice,
        product.marginPerPacket,
      ],
    );

    final List<ProductModel> filtered = ListQuery.filter<ProductModel>(
      source: searched,
      filters: source.filters,
      fieldValue: _fieldValue,
    );

    final List<ProductModel> sorted = ListQuery.sort<ProductModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<ProductModel> paged =
        ListQuery.withoutPagination<ProductModel>(source: sorted);

    return source.copyWith(
      visibleProducts: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(ProductModel product, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_NAME:
        return product.name;
      case AppStrings.FILTER_BY_CROP:
        return product.cropName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(ProductModel product, String field) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return product.name.toLowerCase();
      case AppStrings.SORT_BY_BUYING_PRICE:
        return product.buyingPriceValue;
      case AppStrings.SORT_BY_SELLING_PRICE:
        return product.sellingPriceValue;
      case AppStrings.SORT_BY_MARGIN_PER_PACKET:
        return product.marginPerPacketValue;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
