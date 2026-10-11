import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../bloc/stock_ledger_state.dart';

/// Icon, colour and label for one event family -- the five chips in the
/// "Events" filter row, plus the synthetic opening/closing balance family.
class StockLedgerFamilyMeta {
  final StockLedgerFamily family;
  final String label;
  final Color color;
  final Color tint;
  final IconData icon;

  const StockLedgerFamilyMeta({
    required this.family,
    required this.label,
    required this.color,
    required this.tint,
    required this.icon,
  });
}

/// What one `(event, detail)` pair means for display: which family it
/// belongs to, its title, and (for a count write) whether it is the "up",
/// "down" or "no packing change" variant -- the design's `v` field, which
/// chooses the node's dot style independently of the family colour.
class StockLedgerEventMeta {
  final StockLedgerFamily family;
  final String title;
  final String variant;

  const StockLedgerEventMeta({
    required this.family,
    required this.title,
    this.variant = '',
  });
}

class StockLedgerMeta {
  StockLedgerMeta._();

  static const Map<StockLedgerFamily, StockLedgerFamilyMeta> families = {
    StockLedgerFamily.inward: StockLedgerFamilyMeta(
      family: StockLedgerFamily.inward,
      label: 'Inward',
      color: Color(0xFF3D6FC9),
      tint: Color(0xFFEEF2FB),
      icon: Icons.south_rounded,
    ),
    StockLedgerFamily.waste: StockLedgerFamilyMeta(
      family: StockLedgerFamily.waste,
      label: 'Waste',
      color: Color(0xFFAD6A1F),
      tint: Color(0xFFFBF1E6),
      icon: Icons.delete_outline_rounded,
    ),
    StockLedgerFamily.counts: StockLedgerFamilyMeta(
      family: StockLedgerFamily.counts,
      label: 'Counts',
      color: Color(0xFF8349B8),
      tint: Color(0xFFF4EEFA),
      icon: Icons.checklist_rounded,
    ),
    StockLedgerFamily.orders: StockLedgerFamilyMeta(
      family: StockLedgerFamily.orders,
      label: 'Orders',
      color: Color(0xFF337E82),
      tint: Color(0xFFEBF5F5),
      icon: Icons.description_outlined,
    ),
    StockLedgerFamily.dispatch: StockLedgerFamilyMeta(
      family: StockLedgerFamily.dispatch,
      label: 'Dispatch',
      color: Color(0xFF2E8B4F),
      tint: Color(0xFFEBF6EF),
      icon: Icons.local_shipping_outlined,
    ),
    StockLedgerFamily.balance: StockLedgerFamilyMeta(
      family: StockLedgerFamily.balance,
      label: 'Balance',
      color: AppColors.PRIMARY,
      tint: Color(0xFFE9F3EC),
      icon: Icons.flag_outlined,
    ),
  };

  /// `event` -> family + title. A `detail` further refines the title for the
  /// handful of event types that carry more than one shape of detail text
  /// (see `detailLabel`); most events show the same title regardless of
  /// detail.
  static StockLedgerEventMeta eventMeta(String event, String? detail) {
    switch (event) {
      case 'OPENING_BALANCE':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.balance,
          title: 'Opening balance',
        );
      case 'CLOSING_BALANCE':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.balance,
          title: 'Closing balance',
        );
      case 'INWARD_OPERATIONS':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.inward,
          title: 'Inward',
        );
      case 'RAW_WASTED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.waste,
          title: 'Waste',
        );
      case 'PACKED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.counts,
          title: 'Packed',
          variant: 'packed',
        );
      case 'STOCK_ADJUSTED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.counts,
          title: 'Stock adjusted',
          variant: 'adjusted',
        );
      case 'STOCK_COUNTED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.counts,
          title: 'Stock counted',
          variant: 'counted',
        );
      case 'ORDER_CONFIRMED':
        return StockLedgerEventMeta(
          family: StockLedgerFamily.orders,
          title: detail == 'CUSTOM_ORDER_CREATED'
              ? 'Custom order created'
              : 'Order confirmed',
        );
      case 'ORDER_EDITED':
        return StockLedgerEventMeta(
          family: StockLedgerFamily.orders,
          title: detail == 'CUSTOM_ORDER_LINES_CHANGED'
              ? 'Custom order edited'
              : 'Order edited',
        );
      case 'ORDER_RELEASED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.orders,
          title: 'Order released',
        );
      case 'ORDER_DISPATCHED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.dispatch,
          title: 'Order dispatched',
        );
      case 'DISPATCH_REVERTED':
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.dispatch,
          title: 'Dispatch reverted',
          variant: 'revert',
        );
      case 'RETURN_OPERATIONS':
        return StockLedgerEventMeta(
          family: StockLedgerFamily.dispatch,
          title: detail == 'RETURN_ACCEPT_REVERTED'
              ? 'Return accept reverted'
              : 'Return accepted',
          variant: detail == 'RETURN_ACCEPT_REVERTED' ? 'revert' : '',
        );
      default:
        return const StockLedgerEventMeta(
          family: StockLedgerFamily.counts,
          title: 'Stock event',
        );
    }
  }

  /// A short, human label for the `detail` code shown as the pill next to the
  /// title -- blank details (balance rows, `DISPATCH_REVERTED`) show nothing.
  static String detailLabel(String? detail) {
    switch (detail) {
      case null:
        return '';
      case 'RAW_LOT_IN_USE':
        return 'Raw lot in use';
      case 'RAW_LOT_REJECTED':
        return 'Lot rejected';
      case 'RAW_LOT_BACK_TO_LAB':
        return 'Back to lab';
      case 'RAW_LOT_DELETED':
        return 'Lot deleted';
      case 'OTHER_MATERIAL_RECEIVED':
        return 'Packing material received';
      case 'OTHER_MATERIAL_EDITED':
        return 'Packing material edited';
      case 'OTHER_MATERIAL_DELETED':
        return 'Packing material deleted';
      case 'WASTE_RECORDED':
        return 'Recorded';
      case 'WASTE_EDITED':
        return 'Edited';
      case 'WASTE_DELETED':
        return 'Deleted';
      case 'BAG_COUNT':
        return 'Bag count';
      case 'LOOSE_COUNT':
        return 'Loose count';
      case 'COUNT_DELETED':
        return 'Count deleted';
      case 'CARRIED_FORWARD':
        return 'Carried forward';
      case 'ORDER_VERIFIED':
        return 'Verified';
      case 'ORDER_LINES_CHANGED':
        return 'Lines changed';
      case 'CUSTOM_ORDER_LINES_CHANGED':
        return 'Lines changed';
      case 'HELD':
        return 'Held';
      case 'UNVERIFIED':
        return 'Unverified';
      case 'REJECTED':
        return 'Rejected';
      case 'CUSTOM_ORDER_WITHDRAWN':
        return 'Withdrawn';
      case 'PARTIAL':
        return 'Partial';
      case 'FULL':
        return 'Full';
      case 'CUSTOM_ORDER_CREATED':
        return 'Custom order created';
      case 'RETURN_ACCEPTED':
        return 'Return accepted';
      case 'RETURN_ACCEPT_REVERTED':
        return 'Reverted';
      default:
        return detail
            .split('_')
            .map((w) => w.isEmpty ? w : '${w[0]}${w.substring(1).toLowerCase()}')
            .join(' ');
    }
  }

  /// Label + icon for one `source.kind` -- the chip on an event card that
  /// opens/clears the cross-chain highlight.
  static (String, IconData) sourceKindMeta(String kind) {
    switch (kind) {
      case 'raw':
        return ('Raw lot', Icons.inventory_2_outlined);
      case 'other':
        return ('Packing material', Icons.receipt_outlined);
      case 'waste':
        return ('Waste entry', Icons.delete_outline_rounded);
      case 'bag':
        return ('Bag count', Icons.checklist_rounded);
      case 'loose':
        return ('Loose count', Icons.checklist_rounded);
      case 'order':
        return ('Order', Icons.receipt_long_outlined);
      case 'corder':
        return ('Custom order', Icons.receipt_long_outlined);
      case 'return':
        return ('Return order', Icons.assignment_return_outlined);
      default:
        return (kind, Icons.circle_outlined);
    }
  }
}
