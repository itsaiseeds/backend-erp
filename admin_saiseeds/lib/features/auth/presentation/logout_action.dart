import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../../core/routing/route_constants.dart';
import '../../../core/services/metadata_service.dart';
import '../../../core/services/session_guard.dart';
import '../data/auth_repository.dart';
import 'bloc/auth_bloc.dart';
import 'bloc/auth_event.dart';
import 'bloc/session_cubit.dart';

class LogoutAction {
  LogoutAction._();

  static Future<void> run(BuildContext context) async {
    final authBloc = context.read<AuthBloc>();
    final sessionCubit = context.read<SessionCubit>();
    final authRepository = context.read<AuthRepository>();
    final router = GoRouter.of(context);

    await authRepository.revokeServerSession();
    await SessionGuard.endSession();
    MetadataService.instance.reset();

    authBloc.add(const AuthSignedOut());
    sessionCubit.clear();

    router.go(Routes.LOGIN);
  }
}
