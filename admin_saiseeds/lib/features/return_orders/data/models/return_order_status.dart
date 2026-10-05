import '../../../../core/constants/app_strings.dart';

enum ReturnOrderStatus { pending, accepted, rejected, unknown }

class ReturnOrderStatusX {
  ReturnOrderStatusX._();

  static const String PENDING = 'RETURN_PENDING';
  static const String ACCEPTED = 'RETURN_ACCEPTED';
  static const String REJECTED = 'RETURN_REJECTED';

  /// Accepting and rejecting are both decisions on a return that has not been
  /// decided yet, so both start from PENDING.
  static const Set<ReturnOrderStatus> DECIDABLE = {ReturnOrderStatus.pending};

  static ReturnOrderStatus fromRaw(String raw) {
    switch (raw.trim().toUpperCase()) {
      case PENDING:
        return ReturnOrderStatus.pending;
      case ACCEPTED:
        return ReturnOrderStatus.accepted;
      case REJECTED:
        return ReturnOrderStatus.rejected;
      default:
        return ReturnOrderStatus.unknown;
    }
  }

  static String rawOf(ReturnOrderStatus status) {
    switch (status) {
      case ReturnOrderStatus.pending:
        return PENDING;
      case ReturnOrderStatus.accepted:
        return ACCEPTED;
      case ReturnOrderStatus.rejected:
        return REJECTED;
      case ReturnOrderStatus.unknown:
        return '';
    }
  }

  static String labelOf(ReturnOrderStatus status) {
    switch (status) {
      case ReturnOrderStatus.pending:
        return AppStrings.RETURN_ORDER_STATUS_PENDING;
      case ReturnOrderStatus.accepted:
        return AppStrings.RETURN_ORDER_STATUS_ACCEPTED;
      case ReturnOrderStatus.rejected:
        return AppStrings.RETURN_ORDER_STATUS_REJECTED;
      case ReturnOrderStatus.unknown:
        return AppStrings.TABLE_VALUE_UNAVAILABLE;
    }
  }

  static bool canAccept(ReturnOrderStatus status) => DECIDABLE.contains(status);

  static bool canReject(ReturnOrderStatus status) => DECIDABLE.contains(status);

  /// Unrejecting and reverting both undo a decision already taken, so each is
  /// available only on the decision it undoes.
  static bool canUnreject(ReturnOrderStatus status) =>
      status == ReturnOrderStatus.rejected;

  static bool canRevertAccept(ReturnOrderStatus status) =>
      status == ReturnOrderStatus.accepted;

  /// A return's lines are only editable before anyone has acted on them.
  static bool canEdit(ReturnOrderStatus status) => DECIDABLE.contains(status);
}
