import '../../../core/constants/app_strings.dart';
import '../../../core/constants/user_roles.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/auth_endpoints.dart';
import '../../../core/services/session_guard.dart';
import '../../../core/services/storage_service.dart';
import 'models/auth_session.dart';

class AuthRepository {
  final ApiClient _apiClient;

  const AuthRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  Future<AuthSession> verifyOtp({
    required String phoneNumber,
    required String otp,
  }) async {
    final response = await _apiClient.post(
      AuthEndpoints.verifyOtp,
      body: {'phone_number': phoneNumber, 'otp': otp},
    );

    if (response is! Map) {
      throw const ApiException(
        message: AppStrings.ERROR_UNEXPECTED_RESPONSE,
      );
    }

    final session = AuthSession.fromJson(Map<String, dynamic>.from(response));

    if (!UserRoles.canAccessPortal(session.role)) {
      await SessionGuard.endSession();
      throw const ApiException(message: AppStrings.LOGIN_NOT_AUTHORISED);
    }

    await _persistSession(session);
    return session;
  }

  Future<AuthSession?> readStoredSession() async {
    if (!await StorageService.hasCachedProfile()) return null;

    return AuthSession(
      userId: await StorageService.getUserId() ?? 0,
      name: await StorageService.getUserName() ?? '',
      phoneNumber: await StorageService.getUserPhoneNumber() ?? '',
      role: await StorageService.getUserRole() ?? '',
      canCreateAdmin: await StorageService.getCanCreateAdmin(),
      canCreateSalesPerson: await StorageService.getCanCreateSalesPerson(),
    );
  }

  Future<bool> hasValidSession() => SessionGuard.hasValidSession();

  Future<void> clearSession() => SessionGuard.endSession();

  Future<void> revokeServerSession() async {
    try {
      await _apiClient.post(AuthEndpoints.logout);
    } catch (_) {
      return;
    }
  }

  Future<void> _persistSession(AuthSession session) async {
    await StorageService.saveUserId(session.userId);
    await StorageService.saveUserName(session.name);
    await StorageService.saveUserPhoneNumber(session.phoneNumber);
    await StorageService.saveUserRole(session.role);
    await StorageService.saveCanCreateAdmin(session.canCreateAdmin);
    await StorageService.saveCanCreateSalesPerson(session.canCreateSalesPerson);
  }
}
