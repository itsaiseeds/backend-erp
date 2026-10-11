import 'stock_ledger_row_model.dart';

class StockLedgerProductRef {
  final String publicId;
  final String name;

  const StockLedgerProductRef({this.publicId = '', this.name = ''});

  factory StockLedgerProductRef.fromJson(Map<String, dynamic> json) {
    return StockLedgerProductRef(
      publicId: '${json['public_id'] ?? ''}',
      name: '${json['name'] ?? ''}',
    );
  }

  Map<String, dynamic> toJson() => {'public_id': publicId, 'name': name};
}

/// One page of one product's stock ledger over a date range. The server pages
/// a precomputed, cached list of rows -- `count` is the size of the whole
/// range, not just this page.
class StockLedgerResponse {
  final StockLedgerProductRef product;
  final String startDate;
  final String endDate;
  final int count;
  final int page;
  final int pageSize;
  final List<StockLedgerRow> results;

  const StockLedgerResponse({
    required this.product,
    this.startDate = '',
    this.endDate = '',
    this.count = 0,
    this.page = 1,
    this.pageSize = 50,
    this.results = const [],
  });

  factory StockLedgerResponse.fromJson(Map<String, dynamic> json) {
    final dynamic product = json['product'];
    final dynamic results = json['results'];

    return StockLedgerResponse(
      product: product is Map
          ? StockLedgerProductRef.fromJson(Map<String, dynamic>.from(product))
          : const StockLedgerProductRef(),
      startDate: '${json['start_date'] ?? ''}',
      endDate: '${json['end_date'] ?? ''}',
      count: _asInt(json['count']),
      page: _asInt(json['page']),
      pageSize: _asInt(json['page_size']),
      results: results is List
          ? results
                .whereType<Map>()
                .map(
                  (e) => StockLedgerRow.fromJson(Map<String, dynamic>.from(e)),
                )
                .toList()
          : const [],
    );
  }

  int get totalPages => pageSize <= 0 ? 1 : ((count + pageSize - 1) ~/ pageSize);

  bool get hasMorePages => page < totalPages;

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }
}
