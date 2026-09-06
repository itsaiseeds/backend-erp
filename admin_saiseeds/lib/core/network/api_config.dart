import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../config/app_config_keys.dart';

class ApiConfig {
  ApiConfig._();

  static const String _clientName = 'admin-saiseeds-web';

  static String get clientName => _clientName;

  static String get baseUrl {
    const String compiled = String.fromEnvironment(AppConfigKeys.API_BASE_URL);
    final String resolved = compiled.isNotEmpty
        ? compiled
        : dotenv.env[AppConfigKeys.API_BASE_URL] ?? '';
    return resolved.endsWith('/')
        ? resolved.substring(0, resolved.length - 1)
        : resolved;
  }

  static const Duration timeout = Duration(seconds: 60);

  static Map<String, String> get defaultHeaders => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Client': _clientName,
  };
}
