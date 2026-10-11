import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/stock_ledger_endpoints.dart';
import 'models/stock_ledger_response_model.dart';

/// Raised for the server's 429: the per-user, per-product daily build quota is
/// spent. [retryAfterSeconds] is seconds until the IST calendar day turns over,
/// from the server's own `Retry-After` header -- never guessed client-side.
class StockLedgerRateLimitedException implements Exception {
  final int retryAfterSeconds;
  final String message;

  const StockLedgerRateLimitedException({
    required this.retryAfterSeconds,
    required this.message,
  });
}

/// One browser-cached window: the full decoded response (every row, not just
/// one page) plus when the entry stops being trustworthy.
class StockLedgerCacheEntry {
  final Map<String, dynamic> rawJson;
  final int cachedAtMs;
  final int expiresAtMs;

  const StockLedgerCacheEntry({
    required this.rawJson,
    required this.cachedAtMs,
    required this.expiresAtMs,
  });

  factory StockLedgerCacheEntry.fromJson(Map<String, dynamic> json) {
    return StockLedgerCacheEntry(
      rawJson: Map<String, dynamic>.from(json['response'] as Map),
      cachedAtMs: json['cached_at_ms'] as int? ?? 0,
      expiresAtMs: json['expires_at_ms'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
    'response': rawJson,
    'cached_at_ms': cachedAtMs,
    'expires_at_ms': expiresAtMs,
  };

  bool get isFresh => DateTime.now().millisecondsSinceEpoch < expiresAtMs;

  Duration get age =>
      Duration(milliseconds: DateTime.now().millisecondsSinceEpoch - cachedAtMs);
}

/// What one `(product, start_date, end_date)` window came back as, and from
/// where -- so the screen can show "loaded from cache" honestly rather than
/// assuming every successful load just hit the network.
class StockLedgerResult {
  final StockLedgerResponse response;
  final bool fromCache;
  final Duration? cacheAge;

  const StockLedgerResult({
    required this.response,
    required this.fromCache,
    this.cacheAge,
  });
}

/// Fetches one product's stock ledger, with a browser-local cache in front of
/// the server's own cache + daily-build quota (see `ProductStockLedgerView`).
///
/// Two layers, two different jobs:
/// - The **server** caches a window for everyone (closed windows a day, open
///   ones 5 minutes) and refuses a *build* beyond 2 per product per day --
///   but still answers instantly from its own cache even once that quota is
///   spent.
/// - This **browser cache** saves the round-trip entirely on a repeat visit:
///   the admin re-opens the same product/range and sees the chain before any
///   request goes out, honouring the server's own `Cache-Control` freshness
///   window so it never shows a window as current for longer than the server
///   itself would.
class StockLedgerRepository {
  final ApiClient _apiClient;

  const StockLedgerRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  static const String _cacheKeyPrefix = 'stock_ledger_cache_v1_';
  static const String _buildCountKeyPrefix = 'stock_ledger_builds_v1_';
  static const int dailyBuildsPerProduct = 2;

  /// The server's own hard ceiling (`MAX_PAGE_SIZE` in
  /// `ProductStockLedgerView`) -- asking for more is a 400.
  static const int _serverMaxPageSize = 200;

  /// `force` skips the browser cache and always asks the server -- a cache hit
  /// there is still free (no quota spent), but this exists for an explicit
  /// "reload" affordance, not for the normal screen-open path.
  Future<StockLedgerResult> fetchLedger({
    required String productPublicId,
    required String startDate,
    required String endDate,
    int page = 1,
    int pageSize = 50,
    bool force = false,
  }) async {
    final String cacheKey = _cacheKeyFor(productPublicId, startDate, endDate);

    if (!force) {
      final StockLedgerCacheEntry? cached = await _readCache(cacheKey);
      if (cached != null && cached.isFresh) {
        final StockLedgerResponse full = StockLedgerResponse.fromJson(
          cached.rawJson,
        );
        return StockLedgerResult(
          response: _paginate(full, page, pageSize),
          fromCache: true,
          cacheAge: cached.age,
        );
      }
    }

    try {
      // The server's own cache holds the whole range keyed on (product,
      // start, end) alone -- page number plays no part in it -- so only the
      // very first page here can ever be a cache miss (a "build"); every
      // further page of the same range is guaranteed a free cache hit. That
      // lets this fetch every row of the range (paging at the server's own
      // ceiling) while still costing at most one unit of quota, and gives
      // the browser cache the complete range to serve any later page from
      // with no further request.
      final ApiResponseWithHeaders first = await _apiClient.getWithHeaders(
        StockLedgerEndpoints.productLedger(productPublicId),
        queryParams: {
          'start_date': startDate,
          'end_date': endDate,
          'page': 1,
          'page_size': _serverMaxPageSize,
        },
      );

      if (first.data is! Map) {
        throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
      }
      final Map<String, dynamic> firstJson = Map<String, dynamic>.from(
        first.data as Map,
      );
      final StockLedgerResponse firstPage = StockLedgerResponse.fromJson(
        firstJson,
      );

      final List<Map<String, dynamic>> allResultsJson = List<
        Map<String, dynamic>
      >.from((firstJson['results'] as List).map((e) => Map<String, dynamic>.from(e as Map)));

      final int totalPages = firstPage.pageSize <= 0
          ? 1
          : ((firstPage.count + firstPage.pageSize - 1) ~/ firstPage.pageSize);
      for (int p = 2; p <= totalPages; p++) {
        final ApiResponseWithHeaders next = await _apiClient.getWithHeaders(
          StockLedgerEndpoints.productLedger(productPublicId),
          queryParams: {
            'start_date': startDate,
            'end_date': endDate,
            'page': p,
            'page_size': _serverMaxPageSize,
          },
        );
        if (next.data is! Map) continue;
        final dynamic nextResults = (next.data as Map)['results'];
        if (nextResults is List) {
          allResultsJson.addAll(
            nextResults.map((e) => Map<String, dynamic>.from(e as Map)),
          );
        }
      }

      final Map<String, dynamic> rawJson = {
        ...firstJson,
        'count': allResultsJson.length,
        'page': 1,
        'page_size': allResultsJson.length,
        'results': allResultsJson,
      };

      final int ttlSeconds = _cacheControlMaxAge(first.headers) ?? 300;
      await _writeCache(
        cacheKey,
        StockLedgerCacheEntry(
          rawJson: rawJson,
          cachedAtMs: DateTime.now().millisecondsSinceEpoch,
          expiresAtMs:
              DateTime.now().millisecondsSinceEpoch + ttlSeconds * 1000,
        ),
      );
      // Not necessarily a *build*: the server's own cache may well have
      // answered this for free (a window someone else already built, or one
      // this browser built earlier today but whose local cache has since
      // expired). There is no header telling us which, so this count is an
      // upper bound on builds used, corrected downward the moment a real
      // 429 arrives -- see `recordRateLimited`.
      await _recordPossibleBuild(productPublicId);

      final StockLedgerResponse full = StockLedgerResponse.fromJson(rawJson);
      return StockLedgerResult(
        response: _paginate(full, page, pageSize),
        fromCache: false,
      );
    } on ApiException catch (e) {
      if (e.statusCode == 429) {
        // Ground truth: the quota really is spent, whatever the local
        // approximate counter currently says.
        await _setBuildsUsedToday(productPublicId, dailyBuildsPerProduct);
        throw StockLedgerRateLimitedException(
          retryAfterSeconds: e.retryAfterSeconds ?? _secondsUntilMidnightIst(),
          message: e.message,
        );
      }
      rethrow;
    }
  }

  /// An upper bound on today's builds for [productPublicId] -- see the note
  /// at the call site that increments it. Never above [dailyBuildsPerProduct].
  Future<int> buildsUsedToday(String productPublicId) async {
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final String key = _buildCountKeyFor(productPublicId);
      final String? raw = prefs.getString(key);
      if (raw == null) return 0;
      final dynamic decoded = jsonDecode(raw);
      if (decoded is! Map) return 0;
      final String day = decoded['day'] as String? ?? '';
      if (day != _todayIst()) return 0;
      final int count = decoded['count'] as int? ?? 0;
      return count.clamp(0, dailyBuildsPerProduct);
    } catch (_) {
      return 0;
    }
  }

  Future<void> _recordPossibleBuild(String productPublicId) async {
    final int current = await buildsUsedToday(productPublicId);
    await _setBuildsUsedToday(productPublicId, current + 1);
  }

  Future<void> _setBuildsUsedToday(String productPublicId, int count) async {
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      await prefs.setString(
        _buildCountKeyFor(productPublicId),
        jsonEncode({
          'day': _todayIst(),
          'count': count.clamp(0, dailyBuildsPerProduct),
        }),
      );
    } catch (_) {
      // Best-effort only -- the allowance chip is informational, never a
      // client-side gate (the server is the only thing that actually refuses
      // a build).
    }
  }

  String _buildCountKeyFor(String productPublicId) =>
      '$_buildCountKeyPrefix$productPublicId';

  static String _todayIst() {
    final DateTime nowIst = DateTime.now().toUtc().add(
      const Duration(hours: 5, minutes: 30),
    );
    return '${nowIst.year.toString().padLeft(4, '0')}-'
        '${nowIst.month.toString().padLeft(2, '0')}-'
        '${nowIst.day.toString().padLeft(2, '0')}';
  }

  StockLedgerResponse _paginate(
    StockLedgerResponse full,
    int page,
    int pageSize,
  ) {
    final int offset = (page - 1) * pageSize;
    final int end = (offset + pageSize).clamp(0, full.results.length);
    return StockLedgerResponse(
      product: full.product,
      startDate: full.startDate,
      endDate: full.endDate,
      count: full.results.length,
      page: page,
      pageSize: pageSize,
      results: offset >= full.results.length
          ? const []
          : full.results.sublist(offset, end),
    );
  }

  static int? _cacheControlMaxAge(dynamic headers) {
    try {
      final String? raw = headers?.value('cache-control') as String?;
      if (raw == null) return null;
      final RegExpMatch? match = RegExp(
        r'max-age=(\d+)',
      ).firstMatch(raw);
      if (match == null) return null;
      return int.tryParse(match.group(1)!);
    } catch (_) {
      return null;
    }
  }

  static int _secondsUntilMidnightIst() {
    final DateTime nowUtc = DateTime.now().toUtc();
    final DateTime nowIst = nowUtc.add(const Duration(hours: 5, minutes: 30));
    final DateTime midnightIst = DateTime(
      nowIst.year,
      nowIst.month,
      nowIst.day,
    ).add(const Duration(days: 1));
    return midnightIst.difference(nowIst).inSeconds.clamp(1, 24 * 3600);
  }

  String _cacheKeyFor(String productPublicId, String startDate, String endDate) =>
      '$_cacheKeyPrefix$productPublicId:$startDate:$endDate';

  Future<StockLedgerCacheEntry?> _readCache(String key) async {
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final String? raw = prefs.getString(key);
      if (raw == null || raw.isEmpty) return null;
      final dynamic decoded = jsonDecode(raw);
      if (decoded is! Map) return null;
      return StockLedgerCacheEntry.fromJson(Map<String, dynamic>.from(decoded));
    } catch (_) {
      return null;
    }
  }

  Future<void> _writeCache(String key, StockLedgerCacheEntry entry) async {
    try {
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, jsonEncode(entry.toJson()));
    } catch (_) {
      // A full/unavailable localStorage must never break the screen -- the
      // ledger still renders from the response just fetched, it simply will
      // not be there on the next visit.
    }
  }
}
