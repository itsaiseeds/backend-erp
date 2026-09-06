import 'package:flutter/material.dart';
import '../../../../core/theme/app_spacing.dart';
import '../widgets/launching_soon_panel.dart';

class DashboardOverviewView extends StatelessWidget {
  const DashboardOverviewView({super.key});

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(AppSpacing.lg),
      child: LaunchingSoonPanel(),
    );
  }
}
