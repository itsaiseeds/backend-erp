import 'package:flutter_bloc/flutter_bloc.dart';

abstract class SafeCubit<T> extends Cubit<T> {
  SafeCubit(super.initialState);

  @override
  void emit(T state) {
    if (isClosed) return;
    super.emit(state);
  }
}
