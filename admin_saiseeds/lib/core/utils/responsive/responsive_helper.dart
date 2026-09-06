import 'package:flutter/widgets.dart';
import '../../constants/app_breakpoints.dart';

class ResponsiveHelper {
  ResponsiveHelper._();

  static double _widthOf(BuildContext context) =>
      MediaQuery.sizeOf(context).width;

  static bool isDesktop(BuildContext context) =>
      _widthOf(context) >= AppBreakpoints.desktop;

  static bool isTablet(BuildContext context) {
    final width = _widthOf(context);
    return width >= AppBreakpoints.tablet && width < AppBreakpoints.desktop;
  }

  static bool isMobile(BuildContext context) =>
      _widthOf(context) < AppBreakpoints.tablet;
}
