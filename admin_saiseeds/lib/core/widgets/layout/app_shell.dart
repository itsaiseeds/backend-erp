import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

class AppShell extends StatelessWidget {
  final Widget sidebar;
  final Widget content;
  final bool isCollapsed;

  static const Duration _collapseDuration = Duration(milliseconds: 300);
  static const Curve _collapseCurve = Curves.easeInOutCubic;

  const AppShell({
    super.key,
    required this.sidebar,
    required this.content,
    required this.isCollapsed,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.BACKGROUND_TINTED,
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AnimatedContainer(
            duration: _collapseDuration,
            curve: _collapseCurve,
            width: isCollapsed
                ? AppSizes.sidebarCollapsedWidth
                : AppSizes.sidebarExpandedWidth,
            child: sidebar,
          ),
          Expanded(child: content),
        ],
      ),
    );
  }
}
