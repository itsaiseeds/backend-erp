import 'package:flutter/widgets.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/config/app_config_keys.dart';
import 'package:admin_saiseeds/core/network/api_config.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('.env.prod points at the production host', () async {
    await dotenv.load(fileName: AppConfigKeys.ENV_FILE_PROD);

    final base = ApiConfig.baseUrl;
    debugPrint('prod baseUrl = "$base"');

    expect(base, 'https://sai-seeds.onrender.com');
    expect(base.contains('localhost'), isFalse);
    expect(base.contains('preprod'), isFalse);
  });

  test('otp verify composes to the production URL', () async {
    await dotenv.load(fileName: AppConfigKeys.ENV_FILE_PROD);

    final url = Uri.parse(ApiConfig.baseUrl)
        .resolve('/api/sales-admin/auth/otp/verify')
        .toString();
    debugPrint('verify URL = $url');

    expect(url,
        'https://sai-seeds.onrender.com/api/sales-admin/auth/otp/verify');
  });
}
