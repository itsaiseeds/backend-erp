import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/bloc/safe_cubit.dart';

class _CounterCubit extends SafeCubit<int> {
  _CounterCubit() : super(0);

  void bump() => emit(state + 1);

  Future<void> bumpAfter(Future<void> gate) async {
    await gate;
    emit(state + 1);
  }
}

void main() {
  test('emits normally while open', () {
    final cubit = _CounterCubit();

    cubit.bump();

    expect(cubit.state, 1);
    cubit.close();
  });

  test('an emit after close is dropped instead of throwing', () async {
    final cubit = _CounterCubit();
    await cubit.close();

    expect(cubit.bump, returnsNormally);
    expect(cubit.state, 0);
  });

  test('an in-flight async emit resolving after close does not throw', () async {
    final cubit = _CounterCubit();
    final gate = Future<void>.delayed(const Duration(milliseconds: 20));

    final pending = cubit.bumpAfter(gate);
    await cubit.close();

    await expectLater(pending, completes);
    expect(cubit.state, 0);
  });
}
