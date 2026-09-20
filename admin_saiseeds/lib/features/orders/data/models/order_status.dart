import '../../../../core/constants/app_strings.dart';

enum OrderStatus {
  booked,
  underReview,
  confirmed,
  dispatched,
  delivered,
  onHold,
  rejected,
  unknown,
}

class OrderStatusX {
  OrderStatusX._();

  static const String BOOKED = 'BOOKED';
  static const String UNDER_REVIEW = 'UNDER_REVIEW';
  static const String CONFIRMED = 'CONFIRMED';
  static const String DISPATCHED = 'DISPATCHED';
  static const String DELIVERED = 'DELIVERED';
  static const String ON_HOLD = 'ON_HOLD';
  static const String REJECTED = 'REJECTED';

  static const Set<OrderStatus> VERIFIABLE = {
    OrderStatus.booked,
    OrderStatus.underReview,
    OrderStatus.onHold,
  };

  static const Set<OrderStatus> UNVERIFIABLE = {OrderStatus.confirmed};

  static const Set<OrderStatus> HOLDABLE = {
    OrderStatus.booked,
    OrderStatus.underReview,
    OrderStatus.confirmed,
  };

  static const Set<OrderStatus> REJECTABLE = {
    OrderStatus.booked,
    OrderStatus.underReview,
    OrderStatus.confirmed,
    OrderStatus.onHold,
  };

  static const Set<OrderStatus> EDITABLE = {
    OrderStatus.booked,
    OrderStatus.underReview,
    OrderStatus.confirmed,
    OrderStatus.onHold,
    OrderStatus.rejected,
  };

  static OrderStatus fromRaw(String raw) {
    switch (raw.trim().toUpperCase()) {
      case BOOKED:
        return OrderStatus.booked;
      case UNDER_REVIEW:
        return OrderStatus.underReview;
      case CONFIRMED:
        return OrderStatus.confirmed;
      case DISPATCHED:
        return OrderStatus.dispatched;
      case DELIVERED:
        return OrderStatus.delivered;
      case ON_HOLD:
        return OrderStatus.onHold;
      case REJECTED:
        return OrderStatus.rejected;
      default:
        return OrderStatus.unknown;
    }
  }

  static String rawOf(OrderStatus status) {
    switch (status) {
      case OrderStatus.booked:
        return BOOKED;
      case OrderStatus.underReview:
        return UNDER_REVIEW;
      case OrderStatus.confirmed:
        return CONFIRMED;
      case OrderStatus.dispatched:
        return DISPATCHED;
      case OrderStatus.delivered:
        return DELIVERED;
      case OrderStatus.onHold:
        return ON_HOLD;
      case OrderStatus.rejected:
        return REJECTED;
      case OrderStatus.unknown:
        return '';
    }
  }

  static String labelOf(OrderStatus status) {
    switch (status) {
      case OrderStatus.booked:
        return AppStrings.ORDER_STATUS_BOOKED;
      case OrderStatus.underReview:
        return AppStrings.ORDER_STATUS_UNDER_REVIEW;
      case OrderStatus.confirmed:
        return AppStrings.ORDER_STATUS_CONFIRMED;
      case OrderStatus.dispatched:
        return AppStrings.ORDER_STATUS_DISPATCHED;
      case OrderStatus.delivered:
        return AppStrings.ORDER_STATUS_DELIVERED;
      case OrderStatus.onHold:
        return AppStrings.ORDER_STATUS_ON_HOLD;
      case OrderStatus.rejected:
        return AppStrings.ORDER_STATUS_REJECTED;
      case OrderStatus.unknown:
        return AppStrings.TABLE_VALUE_UNAVAILABLE;
    }
  }

  static bool canVerify(OrderStatus status) => VERIFIABLE.contains(status);

  static bool canUnverify(OrderStatus status) => UNVERIFIABLE.contains(status);

  static bool canHold(OrderStatus status) => HOLDABLE.contains(status);

  static bool canReject(OrderStatus status) => REJECTABLE.contains(status);

  static bool canEdit(OrderStatus status) => EDITABLE.contains(status);
}
