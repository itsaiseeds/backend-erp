import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'route_constants.dart';
import '../services/session_guard.dart';
import '../widgets/feedback/not_found_screen.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';

class AppRouter {
  AppRouter._();

  static final GoRouter router = GoRouter(
    initialLocation: Routes.DASHBOARD,
    debugLogDiagnostics: false,
    refreshListenable: _SessionRefreshNotifier(),
    redirect: _guard,
    errorBuilder: (context, state) =>
        const SelectionArea(child: NotFoundScreen()),
    routes: [
      GoRoute(
        path: Routes.LOGIN,
        name: RouteNames.LOGIN,
        pageBuilder: (context, state) =>
            _buildPage(state: state, child: const LoginScreen()),
      ),
      GoRoute(
        path: Routes.DASHBOARD,
        name: RouteNames.DASHBOARD,
        pageBuilder: (context, state) => _buildPage(
          state: state,
          child: DashboardScreen(
            tab: state.uri.queryParameters[RouteQueryParams.TAB],
          ),
        ),
      ),
      GoRoute(
        path: Routes.NOT_FOUND,
        name: RouteNames.NOT_FOUND,
        pageBuilder: (context, state) =>
            _buildPage(state: state, child: const NotFoundScreen()),
      ),
    ],
  );

  static String? _guard(BuildContext context, GoRouterState state) {
    final bool isLoginRoute = state.matchedLocation == Routes.LOGIN;
    final bool hasSession = SessionGuard.hasSessionSync;

    if (!hasSession) return isLoginRoute ? null : Routes.LOGIN;
    return isLoginRoute ? Routes.DASHBOARD : null;
  }

  static CustomTransitionPage<void> _buildPage({
    required GoRouterState state,
    required Widget child,
  }) {
    return CustomTransitionPage<void>(
      key: state.pageKey,
      child: SelectionArea(child: child),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(
          opacity: CurvedAnimation(parent: animation, curve: Curves.easeIn),
          child: child,
        );
      },
      transitionDuration: const Duration(milliseconds: 180),
    );
  }
}

class _SessionRefreshNotifier extends ChangeNotifier {
  _SessionRefreshNotifier() {
    SessionGuard.sessionListenable.addListener(notifyListeners);
  }

  @override
  void dispose() {
    SessionGuard.sessionListenable.removeListener(notifyListeners);
    super.dispose();
  }
}
