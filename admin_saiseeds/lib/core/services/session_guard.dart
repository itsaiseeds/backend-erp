import 'package:flutter/foundation.dart';
import '../network/api_client.dart';
import '../network/endpoints/utilities_endpoints.dart';
import 'storage_service.dart';

class SessionGuard {
  SessionGuard._();

  static final ValueNotifier<bool> _hasSession = ValueNotifier<bool>(false);

  static ApiClient? _apiClient;

  static Future<ApiProbeResult> Function(String endpoint)? _prober;

  static ValueListenable<bool> get sessionListenable => _hasSession;

  static bool get hasSessionSync => _hasSession.value;

  static set apiClient(ApiClient client) => _apiClient = client;

  @visibleForTesting
  static set prober(Future<ApiProbeResult> Function(String endpoint)? value) =>
      _prober = value;

  static Future<bool> refresh() async {
    final bool isValid = await hasValidSession();
    _hasSession.value = isValid;
    return isValid;
  }

  static Future<bool> hasValidSession() => _verifyWithServer();

  static Future<void> endSession() async {
    await StorageService.clearSession();
    _hasSession.value = false;
  }

  static Future<bool> _verifyWithServer() async {
    late final ApiProbeResult result;
    try {
      final Future<ApiProbeResult> Function(String) probe =
          _prober ?? (_apiClient ??= ApiClient()).probe;
      result = await probe(UtilitiesEndpoints.reauthenticate);
    } catch (_) {
      return _cachedProfileFallback();
    }

    if (result.isSuccess) {
      await _cacheProfileFrom(result.data);
      return true;
    }

    if (result.isUnauthorized) {
      await StorageService.clearSession();
      return false;
    }

    return _cachedProfileFallback();
  }

  static Future<bool> _cachedProfileFallback() async {
    try {
      return await StorageService.hasCachedProfile();
    } catch (_) {
      return false;
    }
  }

  static Future<void> _cacheProfileFrom(dynamic data) async {
    if (data is! Map) return;

    final Map<String, dynamic> payload = Map<String, dynamic>.from(data);
    final dynamic user = payload['user'];
    final Map<String, dynamic> userMap = user is Map
        ? Map<String, dynamic>.from(user)
        : payload;

    try {
      final dynamic id = userMap['id'];
      if (id is int) await StorageService.saveUserId(id);

      final dynamic name = userMap['name'];
      if (name is String && name.isNotEmpty) {
        await StorageService.saveUserName(name);
      }

      final dynamic phoneNumber = userMap['phone_number'];
      if (phoneNumber is String && phoneNumber.isNotEmpty) {
        await StorageService.saveUserPhoneNumber(phoneNumber);
      }

      final dynamic role = userMap['role'];
      if (role is String && role.isNotEmpty) {
        await StorageService.saveUserRole(role);
      }

      final dynamic canCreateAdmin =
          payload['can_create_admin'] ?? userMap['can_create_admin'];
      if (canCreateAdmin is bool) {
        await StorageService.saveCanCreateAdmin(canCreateAdmin);
      }

      final dynamic canCreateSalesPerson =
          payload['can_create_sales_person'] ??
          userMap['can_create_sales_person'];
      if (canCreateSalesPerson is bool) {
        await StorageService.saveCanCreateSalesPerson(canCreateSalesPerson);
      }
    } catch (_) {
      return;
    }
  }
}
