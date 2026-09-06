import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/routing/route_constants.dart';
import '../../../core/services/metadata_service.dart';
import '../../../core/services/session_guard.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/utils/responsive/responsive_helper.dart';
import '../../../core/utils/toast_utils.dart';
import 'bloc/auth_bloc.dart';
import 'bloc/auth_state.dart';
import 'bloc/session_cubit.dart';
import 'widgets/login_brand_panel.dart';
import 'widgets/login_card_header.dart';
import 'widgets/login_form.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const int _brandPanelFlex = 1;
  static const int _formPanelFlex = 1;
  static const double _formMaxWidth = 420.0;
  static const double _compactBrandHeight = 120.0;

  @override
  void initState() {
    super.initState();
    if (!SessionGuard.wasRoleRejected) return;
    SessionGuard.clearRoleRejection();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ToastUtils.showError(
        context,
        AppStrings.LOGIN_FAILED_TITLE,
        description: AppStrings.LOGIN_NOT_AUTHORISED,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state.status == AuthStatus.success) {
          context.read<SessionCubit>().load();
          final router = GoRouter.of(context);
          SessionGuard.refresh().then((_) {
            MetadataService.instance.loadCities(forceRefresh: true);
            router.go(Routes.DASHBOARD);
          });
          return;
        }
        if (state.status == AuthStatus.failure && state.errorMessage != null) {
          ToastUtils.showError(
            context,
            AppStrings.LOGIN_FAILED_TITLE,
            description: state.errorMessage,
          );
        }
      },
      child: Scaffold(
        backgroundColor: AppColors.BACKGROUND_TINTED,
        body: LayoutBuilder(
          builder: (context, constraints) {
            if (ResponsiveHelper.isMobile(context)) {
              return _CompactLayout(
                availableHeight: constraints.maxHeight,
                brandHeight: _compactBrandHeight,
                formMaxWidth: _formMaxWidth,
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: const [
                Expanded(flex: _brandPanelFlex, child: LoginBrandPanel()),
                Expanded(
                  flex: _formPanelFlex,
                  child: _FormPanel(maxWidth: _formMaxWidth),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CompactLayout extends StatelessWidget {
  final double availableHeight;
  final double brandHeight;
  final double formMaxWidth;

  const _CompactLayout({
    required this.availableHeight,
    required this.brandHeight,
    required this.formMaxWidth,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: ConstrainedBox(
        constraints: BoxConstraints(minHeight: availableHeight),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: brandHeight,
              child: const SafeArea(
                bottom: false,
                child: LoginBrandPanel(isCompact: true),
              ),
            ),
            _FormPanel(maxWidth: formMaxWidth, isScrollable: false),
          ],
        ),
      ),
    );
  }
}

class _FormPanel extends StatelessWidget {
  final double maxWidth;
  final bool isScrollable;

  const _FormPanel({required this.maxWidth, this.isScrollable = true});

  @override
  Widget build(BuildContext context) {
    final bool isCompact = ResponsiveHelper.isMobile(context);

    final Widget content = ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxWidth),
      child: DecoratedBox(
        decoration: const BoxDecoration(
          color: AppColors.SURFACE,
          border: Border.fromBorderSide(BorderSide(color: AppColors.BORDER)),
          borderRadius: BorderRadius.all(Radius.circular(AppRadius.lg)),
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              LoginCardHeader(isCompact: isCompact),
              Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: isCompact ? AppSpacing.lgs : AppSpacing.lg,
                  vertical: isCompact ? AppSpacing.lgs : AppSpacing.lg,
                ),
                child: const LoginForm(),
              ),
            ],
          ),
        ),
      ),
    );

    final EdgeInsets padding = EdgeInsets.symmetric(
      horizontal: isCompact ? AppSpacing.md : AppSpacing.xl,
      vertical: isCompact ? AppSpacing.lg : AppSpacing.xl,
    );

    if (!isScrollable) {
      return Container(
        color: AppColors.BACKGROUND_TINTED,
        padding: padding,
        child: Align(alignment: Alignment.topCenter, child: content),
      );
    }

    return ColoredBox(
      color: AppColors.BACKGROUND_TINTED,
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: padding,
            child: Center(child: content),
          ),
        ),
      ),
    );
  }
}
