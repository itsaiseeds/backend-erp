import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../data/models/field_trip_model.dart';

class FieldTripStatusBadge extends StatelessWidget {
  final FieldTripModel trip;

  const FieldTripStatusBadge({super.key, required this.trip});

  AppBadgeVariant get _variant {
    if (trip.isCompleted) return AppBadgeVariant.success;
    if (trip.isInProgress) return AppBadgeVariant.info;
    if (trip.isApproved) return AppBadgeVariant.neutral;
    return AppBadgeVariant.warning;
  }

  @override
  Widget build(BuildContext context) {
    final String label = trip.statusLabel;
    return AppBadge(
      label: label.isEmpty ? AppStrings.FIELD_TRIP_STATUS_PLANNED : label,
      variant: _variant,
    );
  }
}
