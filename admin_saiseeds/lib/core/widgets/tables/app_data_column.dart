import '../../theme/app_spacing.dart';

class AppDataColumn {
  final String id;
  final String label;
  final double width;
  final bool isCenter;

  const AppDataColumn({
    required this.id,
    required this.label,
    this.width = AppSizes.tableDefaultColumnWidth,
    this.isCenter = false,
  });
}
