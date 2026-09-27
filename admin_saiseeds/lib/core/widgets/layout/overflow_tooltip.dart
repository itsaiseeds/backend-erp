import 'package:flutter/material.dart';
import '../../theme/app_spacing.dart';

/// Wraps [child] in a tooltip only when [text] cannot fit the available
/// width, so a fully visible label never shows a redundant hint.
class OverflowTooltip extends StatelessWidget {
  final String text;
  final TextStyle style;
  final Widget child;

  const OverflowTooltip({
    super.key,
    required this.text,
    required this.style,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (!constraints.hasBoundedWidth) return child;

        final TextPainter painter = TextPainter(
          text: TextSpan(text: text, style: style),
          maxLines: 1,
          textDirection: Directionality.of(context),
          textScaler: MediaQuery.textScalerOf(context),
        )..layout();

        if (painter.width <= constraints.maxWidth) return child;

        return Tooltip(
          message: text,
          preferBelow: false,
          verticalOffset: AppSizes.sidebarTooltipOffset,
          child: child,
        );
      },
    );
  }
}
