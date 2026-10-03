import 'package:flutter/material.dart';
import '../../network/api_config.dart';
import '../../constants/font_sizes.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

/// Small product image used in order line rows.
///
/// Falls back to a neutral tile when the product has no image or the fetch
/// fails, so a missing picture never collapses the row.
class ProductThumbnail extends StatelessWidget {
  static const double defaultSize = 44;

  final String url;
  final double size;

  const ProductThumbnail({
    super.key,
    required this.url,
    this.size = defaultSize,
  });

  @override
  Widget build(BuildContext context) {
    final String resolved = resolve(url);

    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppSpacing.xs),
      ),
      clipBehavior: Clip.antiAlias,
      child: resolved.isEmpty
          ? const _Fallback()
          : Image.network(
              resolved,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stack) => const _Fallback(),
            ),
    );
  }

  /// Turns a relative media path into an absolute one; an already absolute
  /// URL is left alone.
  static String resolve(String path) {
    final String trimmed = path.trim();
    if (trimmed.isEmpty) return '';
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    final String base = ApiConfig.baseUrl;
    if (base.isEmpty) return trimmed;
    return trimmed.startsWith('/') ? '$base$trimmed' : '$base/$trimmed';
  }
}

class _Fallback extends StatelessWidget {
  const _Fallback();

  @override
  Widget build(BuildContext context) {
    return const Icon(
      Icons.inventory_2_outlined,
      size: AppFontSizes.FONT_18,
      color: AppColors.TEXT_DISABLED,
    );
  }
}
