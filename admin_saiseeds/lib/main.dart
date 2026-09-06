import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:toastification/toastification.dart';
import 'core/config/app_config_keys.dart';
import 'core/config/observability_config.dart';
import 'core/constants/app_strings.dart';
import 'core/network/api_client.dart';
import 'core/routing/app_router.dart';
import 'core/services/session_guard.dart';
import 'core/theme/app_theme.dart';
import 'core/utils/app_scroll_behavior.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/presentation/bloc/auth_bloc.dart';
import 'features/auth/presentation/bloc/session_cubit.dart';

Future<void> _bootstrap() async {
  WidgetsFlutterBinding.ensureInitialized();
  usePathUrlStrategy();

  await dotenv.load(fileName: AppConfigKeys.ENV_FILE);

  final apiClient = ApiClient();
  SessionGuard.apiClient = apiClient;
  await SessionGuard.refresh();

  runApp(AdminSaiseedsApp(apiClient: apiClient));
}

Future<void> main() async {
  if (!ObservabilityConfig.isEnabled) {
    await _bootstrap();
    return;
  }

  await SentryFlutter.init(
    (options) => options
      ..dsn = ObservabilityConfig.sentryDsn
      ..tracesSampleRate = ObservabilityConfig.tracesSampleRate
      ..enableAutoSessionTracking = false
      ..environment = ObservabilityConfig.environment
      ..release = ObservabilityConfig.release,
    appRunner: _bootstrap,
  );
}

class AdminSaiseedsApp extends StatelessWidget {
  final ApiClient? apiClient;

  const AdminSaiseedsApp({super.key, this.apiClient});

  @override
  Widget build(BuildContext context) {
    final authRepository = AuthRepository(
      apiClient: apiClient ?? ApiClient(),
    );

    return RepositoryProvider<AuthRepository>.value(
      value: authRepository,
      child: MultiBlocProvider(
        providers: [
          BlocProvider(create: (_) => AuthBloc(authRepository: authRepository)),
          BlocProvider(
            create: (_) =>
                SessionCubit(authRepository: authRepository)..load(),
          ),
        ],
        child: ToastificationWrapper(
          child: MaterialApp.router(
            title: AppStrings.APP_NAME,
            routerConfig: AppRouter.router,
            theme: AppTheme.light,
            scrollBehavior: const AppScrollBehavior(),
            debugShowCheckedModeBanner: false,
          ),
        ),
      ),
    );
  }
}
