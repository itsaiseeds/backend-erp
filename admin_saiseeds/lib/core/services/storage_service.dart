import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  StorageService._();

  static const String _userIdKey = 'user_id';
  static const String _userNameKey = 'user_name';
  static const String _userPhoneNumberKey = 'user_phone_number';
  static const String _userRoleKey = 'user_role';
  static const String _canCreateAdminKey = 'can_create_admin';
  static const String _canCreateSalesPersonKey = 'can_create_sales_person';

  static const List<String> _sessionKeys = [
    _userIdKey,
    _userNameKey,
    _userPhoneNumberKey,
    _userRoleKey,
    _canCreateAdminKey,
    _canCreateSalesPersonKey,
  ];

  static Future<int?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_userIdKey);
  }

  static Future<void> saveUserId(int userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_userIdKey, userId);
  }

  static Future<String?> getUserName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userNameKey);
  }

  static Future<void> saveUserName(String name) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userNameKey, name);
  }

  static Future<String?> getUserPhoneNumber() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userPhoneNumberKey);
  }

  static Future<void> saveUserPhoneNumber(String phoneNumber) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userPhoneNumberKey, phoneNumber);
  }

  static Future<String?> getUserRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userRoleKey);
  }

  static Future<void> saveUserRole(String role) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userRoleKey, role);
  }

  static Future<bool> getCanCreateAdmin() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_canCreateAdminKey) ?? false;
  }

  static Future<void> saveCanCreateAdmin(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_canCreateAdminKey, value);
  }

  static Future<bool> getCanCreateSalesPerson() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_canCreateSalesPersonKey) ?? false;
  }

  static Future<void> saveCanCreateSalesPerson(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_canCreateSalesPersonKey, value);
  }

  static Future<bool> hasCachedProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final String? name = prefs.getString(_userNameKey);
    if (name != null && name.isNotEmpty) return true;
    final String? phoneNumber = prefs.getString(_userPhoneNumberKey);
    if (phoneNumber != null && phoneNumber.isNotEmpty) return true;
    final String? role = prefs.getString(_userRoleKey);
    return role != null && role.isNotEmpty;
  }

  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    for (final key in _sessionKeys) {
      await prefs.remove(key);
    }
  }
}
