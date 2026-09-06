import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../data/auth_repository.dart';
import '../../data/models/auth_session.dart';

enum SessionStatus { loading, loaded, absent }

class SessionState extends Equatable {
  final SessionStatus status;
  final AuthSession? session;

  const SessionState._({required this.status, this.session});

  const SessionState.loading() : this._(status: SessionStatus.loading);

  const SessionState.loaded(AuthSession session)
    : this._(status: SessionStatus.loaded, session: session);

  const SessionState.absent() : this._(status: SessionStatus.absent);

  @override
  List<Object?> get props => [status, session];
}

class SessionCubit extends SafeCubit<SessionState> {
  final AuthRepository _authRepository;

  SessionCubit({required AuthRepository authRepository})
    : _authRepository = authRepository,
      super(const SessionState.loading());

  Future<void> load() async {
    try {
      final session = await _authRepository.readStoredSession();
      if (isClosed) return;
      emit(
        session == null
            ? const SessionState.absent()
            : SessionState.loaded(session),
      );
    } catch (_) {
      if (isClosed) return;
      emit(const SessionState.absent());
    }
  }

  void clear() {
    if (isClosed) return;
    emit(const SessionState.absent());
  }
}
