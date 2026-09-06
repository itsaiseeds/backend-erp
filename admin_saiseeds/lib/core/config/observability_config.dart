import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'app_config_keys.dart';

class ObservabilityConfig {
  ObservabilityConfig._();

  static const String _compiledDsn = String.fromEnvironment(
    AppConfigKeys.SENTRY_DSN,
  );

  static const double _releaseTracesSampleRate = 0.01;
  static const double _debugTracesSampleRate = 0.0;

  static const String _fallbackReleaseEnvironment = 'production';
  static const String _fallbackDebugEnvironment = 'development';

  static const String _appName = 'admin_saiseeds';
  static const String _appVersion = '1.0.0+1';

  static String get release => '$_appName@$_appVersion';

  static String get sentryDsn {
    if (_compiledDsn.isNotEmpty) return _compiledDsn;
    return dotenv.maybeGet(AppConfigKeys.SENTRY_DSN) ?? '';
  }

  static bool get isEnabled => sentryDsn.isNotEmpty;

  static double get tracesSampleRate =>
      kReleaseMode ? _releaseTracesSampleRate : _debugTracesSampleRate;

  static String get environment {
    final String configured =
        dotenv.maybeGet(AppConfigKeys.SENTRY_ENVIRONMENT) ?? '';
    if (configured.isNotEmpty) return configured;
    return kReleaseMode
        ? _fallbackReleaseEnvironment
        : _fallbackDebugEnvironment;
  }
}
