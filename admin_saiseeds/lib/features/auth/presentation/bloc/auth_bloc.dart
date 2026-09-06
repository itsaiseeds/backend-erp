import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../data/auth_repository.dart';
import 'auth_event.dart';
import 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final AuthRepository _authRepository;

  AuthBloc({required AuthRepository authRepository})
    : _authRepository = authRepository,
      super(const AuthState.initial()) {
    on<AuthOtpSubmitted>(_onOtpSubmitted);
    on<AuthSignedOut>(_onSignedOut);
  }

  Future<void> _onOtpSubmitted(
    AuthOtpSubmitted event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthState.loading());
    try {
      final session = await _authRepository.verifyOtp(
        phoneNumber: event.phoneNumber,
        otp: event.otp,
      );
      emit(AuthState.success(session));
    } on ApiException catch (e) {
      final message = e.message.trim();
      emit(
        AuthState.failure(
          message.isEmpty ? AppStrings.LOGIN_FAILED : message,
        ),
      );
    } catch (_) {
      emit(const AuthState.failure(AppStrings.LOGIN_FAILED));
    }
  }

  Future<void> _onSignedOut(
    AuthSignedOut event,
    Emitter<AuthState> emit,
  ) async {
    await _authRepository.clearSession();
    emit(const AuthState.initial());
  }
}
