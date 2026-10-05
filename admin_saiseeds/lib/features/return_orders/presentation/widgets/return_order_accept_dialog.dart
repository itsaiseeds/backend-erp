import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_toggle_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/return_order_model.dart';
import '../../data/models/return_recipe_model.dart';
import '../../data/return_orders_repository.dart';

/// Accepting books the returned kilograms back in as inward raw-material stock.
///
/// The packing materials come back too -- bags and labels -- but nothing knows
/// how many of each until an admin says what they are made of. That is what the
/// recipe list is for, so the flag is on by default: the material physically
/// exists, and leaving it out would quietly lose it.
///
/// Selection is held per line, because that is the unit the API's rules are
/// written against: at least one recipe on every line, and never two recipes of
/// the same material type on one line.
class ReturnOrderAcceptDialog extends StatefulWidget {
  final ReturnOrderModel returnOrder;
  final ReturnOrdersRepository repository;
  final ReturnOrderRecipesModel recipes;

  const ReturnOrderAcceptDialog({
    super.key,
    required this.returnOrder,
    required this.repository,
    required this.recipes,
  });

  /// Loads the recipes first, outside the dialog: an empty list and a failed
  /// load are different answers and must not look the same.
  ///
  /// Resolves true only when the accept went through, so the caller can hold
  /// back its success toast on a cancelled dialog.
  static Future<bool> show(
    BuildContext context, {
    required ReturnOrderModel returnOrder,
    required ReturnOrdersRepository repository,
    required Future<ReturnOrderRecipesModel?> Function(String publicId)
    loadRecipes,
  }) async {
    final ReturnOrderRecipesModel? recipes = await loadRecipes(
      returnOrder.publicId,
    );
    if (!context.mounted || recipes == null) return false;

    final bool? accepted = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ReturnOrderAcceptDialog(
        returnOrder: returnOrder,
        repository: repository,
        recipes: recipes,
      ),
    );
    return accepted ?? false;
  }

  @override
  State<ReturnOrderAcceptDialog> createState() =>
      _ReturnOrderAcceptDialogState();
}

class _ReturnOrderAcceptDialogState extends State<ReturnOrderAcceptDialog> {
  bool _includeMaterials = true;

  /// Recipe public ids picked per line index. A [Set] per line is what makes
  /// "one recipe per material type" a local decision rather than a global scan.
  final Map<int, Set<String>> _selected = {};

  bool _isSubmitting = false;
  String? _error;

  bool get _hasAnyRecipe => widget.recipes.lines.any((line) => line.hasRecipes);

  bool get _isValid {
    if (!_includeMaterials) return true;
    if (!_hasAnyRecipe) return false;

    for (int index = 0; index < widget.recipes.lines.length; index++) {
      final ReturnRecipeLineModel line = widget.recipes.lines[index];
      if (!line.hasRecipes) continue;
      if (!(_selected[index]?.isNotEmpty ?? false)) return false;
    }
    return true;
  }

  List<String> get _flatSelection => [
    for (final Set<String> ids in _selected.values) ...ids,
  ];

  void _toggle({
    required int lineIndex,
    required ReturnRecipeLineModel line,
    required ReturnRecipeOptionModel option,
    required bool on,
  }) {
    setState(() {
      final Set<String> current = _selected.putIfAbsent(
        lineIndex,
        () => <String>{},
      );

      if (on) {
        current.removeWhere((id) {
          final ReturnRecipeOptionModel? other = _optionById(line, id);
          return other != null &&
              other.materialTypeKey == option.materialTypeKey;
        });
        current.add(option.publicId);
      } else {
        current.remove(option.publicId);
      }

      if (current.isEmpty) _selected.remove(lineIndex);
      _error = null;
    });
  }

  static ReturnRecipeOptionModel? _optionById(
    ReturnRecipeLineModel line,
    String publicId,
  ) {
    for (final option in line.recipes) {
      if (option.publicId == publicId) return option;
    }
    return null;
  }

  Future<void> _submit() async {
    if (!_isValid) {
      setState(() {
        _error = AppStrings.RETURN_ORDER_ACCEPT_PICK_AT_LEAST_ONE;
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await widget.repository.acceptReturn(
        publicId: widget.returnOrder.publicId,
        includeInOtherRawMaterials: _includeMaterials,
        recipePublicIds: _flatSelection,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSubmitting = false;
        _error = '$e';
      });
      return;
    }

    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.check_circle_outline_rounded,
      title: AppStrings.RETURN_ORDER_ACCEPT_TITLE,
      subtitle: widget.returnOrder.publicId,
      submitLabel: AppStrings.RETURN_ORDER_ACCEPT,
      isSubmitting: _isSubmitting,
      fixedHeight: 620,
      onSubmit: _isSubmitting ? null : _submit,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          _Summary(returnOrder: widget.returnOrder),
          const SizedBox(height: AppSpacing.md),
          AppToggleField(
            label: AppStrings.RETURN_ORDER_ACCEPT_INCLUDE_MATERIALS,
            description: AppStrings.RETURN_ORDER_ACCEPT_INCLUDE_MATERIALS_HINT,
            value: _includeMaterials,
            onChanged: (bool value) => setState(() {
              _includeMaterials = value;
              // The API refuses a body carrying both the flag and recipe ids, so
              // ticking the flag off has to drop the picks with it.
              if (!value) _selected.clear();
              _error = null;
            }),
          ),
          if (_includeMaterials) ...[
            const SizedBox(height: AppSpacing.md),
            const AppHairline(),
            const SizedBox(height: AppSpacing.md),
            _RecipeSection(
              recipes: widget.recipes,
              selected: _selected,
              onToggle: _toggle,
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.md),
            Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
            ),
          ],
        ],
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  final ReturnOrderModel returnOrder;

  const _Summary({required this.returnOrder});

  @override
  Widget build(BuildContext context) {
    return Text(
      AppStrings.RETURN_ORDER_ACCEPT_PENDING_SUMMARY
          .replaceAll('%p', '${returnOrder.totalPackets}')
          .replaceAll('%w', _trim(returnOrder.totalKg))
          .replaceAll('%a', CurrencyFormatter.rupees(returnOrder.totalAmount)),
      style: AppTypography.bodyMedium.copyWith(color: AppColors.TEXT_SECONDARY),
    );
  }

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}

class _RecipeSection extends StatelessWidget {
  final ReturnOrderRecipesModel recipes;
  final Map<int, Set<String>> selected;
  final void Function({
    required int lineIndex,
    required ReturnRecipeLineModel line,
    required ReturnRecipeOptionModel option,
    required bool on,
  })
  onToggle;

  const _RecipeSection({
    required this.recipes,
    required this.selected,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final List<int> withRecipes = [
      for (int i = 0; i < recipes.lines.length; i++)
        if (recipes.lines[i].hasRecipes) i,
    ];

    if (withRecipes.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          SectionTitle(
            title: AppStrings.RETURN_ORDER_ACCEPT_RECIPES_TITLE,
            icon: Icons.layers_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            AppStrings.RETURN_ORDER_ACCEPT_RECIPES_EMPTY,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      );
    }

    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          SectionTitle(
            title: AppStrings.RETURN_ORDER_ACCEPT_RECIPES_TITLE,
            icon: Icons.layers_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.sm),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final int index in withRecipes)
                    _LineBlock(
                      line: recipes.lines[index],
                      selected: selected[index] ?? const {},
                      onToggle: (ReturnRecipeOptionModel option, bool on) =>
                          onToggle(
                            lineIndex: index,
                            line: recipes.lines[index],
                            option: option,
                            on: on,
                          ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LineBlock extends StatelessWidget {
  final ReturnRecipeLineModel line;
  final Set<String> selected;
  final void Function(ReturnRecipeOptionModel option, bool on) onToggle;

  const _LineBlock({
    required this.line,
    required this.selected,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.RETURN_ORDER_ACCEPT_LINE_TITLE
                .replaceAll('%s', line.product.name)
                .replaceAll('%w', line.packetWeightLabel),
            style: AppTypography.labelStrong,
          ),
          const SizedBox(height: AppSpacing.xs),
          ...line.recipes.map(
            (option) => _RecipeTile(
              option: option,
              isSelected: selected.contains(option.publicId),
              onChanged: (bool on) => onToggle(option, on),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecipeTile extends StatelessWidget {
  final ReturnRecipeOptionModel option;
  final bool isSelected;
  final ValueChanged<bool> onChanged;

  const _RecipeTile({
    required this.option,
    required this.isSelected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final String summary = AppStrings.RETURN_ORDER_ACCEPT_RECIPE_SUMMARY
        .replaceAll('%q', option.quantityLabel);

    return CheckboxListTile(
      value: isSelected,
      onChanged: (bool? on) => onChanged(on ?? false),
      // Stock booked against a since-deleted recipe still counts, so a deleted
      // one is offered -- but saying so is the only way the admin can judge it.
      title: Text(option.materialTypeName, style: AppTypography.bodyMedium),
      subtitle: Text(
        option.isDeleted
            ? AppStrings.RETURN_ORDER_ACCEPT_RECIPE_DELETED.replaceAll(
                '%s',
                summary,
              )
            : summary,
        style: AppTypography.bodySmall.copyWith(
          color: option.isDeleted
              ? AppColors.TEXT_DISABLED
              : AppColors.TEXT_SECONDARY,
        ),
      ),
      controlAffinity: ListTileControlAffinity.leading,
      dense: true,
      contentPadding: EdgeInsets.zero,
    );
  }
}
