class StockLedgerEndpoints {
  StockLedgerEndpoints._();

  static const String _base = '/api/sales-admin';

  static String productLedger(String productPublicId) =>
      '$_base/product-stock-ledger/$productPublicId';
}
