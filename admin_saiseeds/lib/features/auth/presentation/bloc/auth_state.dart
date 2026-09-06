import 'package:equatable/equatable.dart';
import '../../data/models/auth_session.dart';

enum AuthStatus { initial, loading, success, failure }

class AuthState extends Equatable {
  final AuthStatus status;
  final String? errorMessage;
  final AuthSession? session;

  const AuthState._({required this.status, this.errorMessage, this.session});

  const AuthState.initial() : this._(status: AuthStatus.initial);

  const AuthState.loading() : this._(status: AuthStatus.loading);

  const AuthState.success(AuthSession session)
    : this._(status: AuthStatus.success, session: session);

  const AuthState.failure(String message)
    : this._(status: AuthStatus.failure, errorMessage: message);

  @override
  List<Object?> get props => [status, errorMessage, session];
}
