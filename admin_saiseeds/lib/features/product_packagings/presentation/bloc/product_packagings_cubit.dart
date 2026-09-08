import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/product_packaging_model.dart';
import '../../data/product_packagings_repository.dart';

enum ProductPackagingsStatus { initial, loading, loaded, failure }

class ProductPackagingsState extends Equatable {
  final ProductPackagingsStatus status;
  final List<ProductPackagingModel> allPackagings;
  final List<ProductPackagingModel> visiblePackagings;
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

  const ProductPackagingsState({
    this.status = ProductPackagingsStatus.initial,
    this.allPackagings = const [],
    this.visiblePackagings = const [],
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
      status == ProductPackagingsStatus.loaded && allPackagings.isEmpty;

  ProductPackagingsState copyWith({
    ProductPackagingsStatus? status,
    List<ProductPackagingModel>? allPackagings,
    List<ProductPackagingModel>? visiblePackagings,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return ProductPackagingsState(
      status: status ?? this.status,
      allPackagings: allPackagings ?? this.allPackagings,
      visiblePackagings: visiblePackagings ?? this.visiblePackagings,
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
    allPackagings,
    visiblePackagings,
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

class ProductPackagingsCubit extends SafeCubit<ProductPackagingsState> {
  final ProductPackagingsRepository _repository;

  ProductPackagingsCubit({required ProductPackagingsRepository repository})
    : _repository = repository,
      super(const ProductPackagingsState());

  Future<void> loadProductPackagings() async {
    emit(
      state.copyWith(status: ProductPackagingsStatus.loading, clearError: true),
    );

    try {
      final List<ProductPackagingModel> packagings = await _repository
          .fetchProductPackagings();
      emit(
        _projected(
          state.copyWith(
            status: ProductPackagingsStatus.loaded,
            allPackagings: packagings,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: ProductPackagingsStatus.failure,
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
    final ProductPackagingsState next = ProductPackagingsState(
      status: state.status,
      allPackagings: state.allPackagings,
      visiblePackagings: state.visiblePackagings,
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

  Future<bool> createProductPackaging({
    required String productPublicId,
    required String packetWeight,
    required String packets,
    required String sellingPrice,
  }) {
    return _mutate(
      () => _repository.createProductPackaging(
        productPublicId: productPublicId,
        packetWeight: packetWeight,
        packets: packets,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<bool> updateProductPackaging({
    required String publicId,
    required String productPublicId,
    required String packetWeight,
    required String packets,
    required String sellingPrice,
  }) {
    return _mutate(
      () => _repository.updateProductPackaging(
        publicId: publicId,
        productPublicId: productPublicId,
        packetWeight: packetWeight,
        packets: packets,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<bool> deleteProductPackaging(String publicId) =>
      _mutate(() => _repository.deleteProductPackaging(publicId));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadProductPackagings();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  ProductPackagingsState _projected(
    ProductPackagingsState source, {
    required int page,
  }) {
    final List<ProductPackagingModel> searched =
        ListQuery.search<ProductPackagingModel>(
          source: source.allPackagings,
          query: source.search,
          searchableValues: (packaging) => [
            packaging.productName,
            packaging.packetWeight,
            packaging.packetsLabel,
            packaging.totalWeight,
            packaging.sellingPrice,
          ],
        );

    final List<ProductPackagingModel> filtered =
        ListQuery.filter<ProductPackagingModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
        );

    final List<ProductPackagingModel> sorted =
        ListQuery.sort<ProductPackagingModel>(
          source: filtered,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<ProductPackagingModel> paged =
        ListQuery.withoutPagination<ProductPackagingModel>(source: sorted);

    return source.copyWith(
      visiblePackagings: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(ProductPackagingModel packaging, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_PRODUCT:
        return packaging.productName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    ProductPackagingModel packaging,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_PRODUCT:
        return packaging.productName.toLowerCase();
      case AppStrings.SORT_BY_PACKET_WEIGHT:
        return packaging.packetWeightValue;
      case AppStrings.SORT_BY_PACKETS:
        return packaging.packets;
      case AppStrings.SORT_BY_TOTAL_WEIGHT:
        return packaging.totalWeightValue;
      case AppStrings.SORT_BY_SELLING_PRICE:
        return packaging.sellingPriceValue;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
