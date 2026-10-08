import 'package:equatable/equatable.dart';

import '../../../../core/bloc/safe_cubit.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/client_model.dart';
import '../../../orders/data/models/child_org_model.dart';

enum ChildClientsStatus { initial, loading, loaded, failure }

class ChildClientsState extends Equatable {
  final ClientModel? parent;
  final ChildClientsStatus status;
  final List<ChildOrgModel> children;
  final String? errorMessage;

  const ChildClientsState({
    this.parent,
    this.status = ChildClientsStatus.initial,
    this.children = const [],
    this.errorMessage,
  });

  ChildClientsState copyWith({
    ClientModel? parent,
    bool clearParent = false,
    ChildClientsStatus? status,
    List<ChildOrgModel>? children,
    String? errorMessage,
    bool clearError = false,
  }) {
    return ChildClientsState(
      parent: clearParent ? null : parent ?? this.parent,
      status: status ?? this.status,
      children: children ?? this.children,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
    );
  }

  bool get isLoading => status == ChildClientsStatus.loading;

  @override
  List<Object?> get props => [parent, status, children, errorMessage];
}

/// Drives the "Child Client Management" tab: pick a parent client, see the
/// delivery places ("child clients") it books orders through. There is no
/// create/edit/delete here -- a child client exists only as a side effect of
/// an order's "Delivery To", so this tab is read-only by nature.
class ChildClientsCubit extends SafeCubit<ChildClientsState> {
  final ClientsRepository _repository;

  ChildClientsCubit({required ClientsRepository repository})
    : _repository = repository,
      super(const ChildClientsState());

  Future<void> selectParent(ClientModel parent) async {
    if (state.parent?.publicId == parent.publicId) return;

    emit(
      state.copyWith(
        parent: parent,
        status: ChildClientsStatus.loading,
        children: const [],
        clearError: true,
      ),
    );

    try {
      final List<ChildOrgModel> children = await _repository
          .fetchClientChildren(parent.publicId);
      if (state.parent?.publicId != parent.publicId) return;
      emit(
        state.copyWith(status: ChildClientsStatus.loaded, children: children),
      );
    } catch (e) {
      if (state.parent?.publicId != parent.publicId) return;
      emit(
        state.copyWith(
          status: ChildClientsStatus.failure,
          errorMessage: '$e',
        ),
      );
    }
  }

  Future<void> refresh() async {
    final ClientModel? parent = state.parent;
    if (parent == null) return;

    emit(state.copyWith(status: ChildClientsStatus.loading, clearError: true));
    try {
      final List<ChildOrgModel> children = await _repository
          .fetchClientChildren(parent.publicId);
      if (state.parent?.publicId != parent.publicId) return;
      emit(
        state.copyWith(status: ChildClientsStatus.loaded, children: children),
      );
    } catch (e) {
      if (state.parent?.publicId != parent.publicId) return;
      emit(
        state.copyWith(
          status: ChildClientsStatus.failure,
          errorMessage: '$e',
        ),
      );
    }
  }
}
