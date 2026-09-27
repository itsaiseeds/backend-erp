import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/parties_service.dart';
import '../../../../core/services/recipes_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/party_picker_field.dart';
import '../../../../core/widgets/inputs/recipe_picker_field.dart';
import '../../../other_raw_materials/data/models/other_material_recipe_model.dart';
import '../../../parties/data/models/party_model.dart';
import '../bloc/other_material_inward_cubit.dart';

class OtherInwardFormDialog extends StatefulWidget {
  const OtherInwardFormDialog({super.key});

  static Future<void> show(
    BuildContext context, {
    required OtherMaterialInwardCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OtherMaterialInwardCubit>.value(
        value: cubit,
        child: const OtherInwardFormDialog(),
      ),
    );
  }

  @override
  State<OtherInwardFormDialog> createState() => _OtherInwardFormDialogState();
}

class _OtherInwardFormDialogState extends State<OtherInwardFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _quantityController = TextEditingController();

  OtherMaterialRecipeModel? _recipe;
  PartyModel? _party;

  bool _isSubmitting = false;
  String? _recipeError;
  String? _partyError;

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  String get _quantityLabel {
    final String unit = _recipe?.unitType.trim() ?? '';
    if (unit.isEmpty) return AppStrings.COLUMN_QUANTITY;
    return '${AppStrings.COLUMN_QUANTITY} ($unit)';
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isRecipeValid = _recipe != null;
    final bool isPartyValid = _party != null;

    setState(() {
      _recipeError = isRecipeValid
          ? null
          : AppStrings.VALIDATION_RECIPE_REQUIRED;
      _partyError = isPartyValid ? null : AppStrings.VALIDATION_PARTY_REQUIRED;
    });

    if (!isFormValid || !isRecipeValid || !isPartyValid) return;

    setState(() => _isSubmitting = true);

    final OtherMaterialInwardCubit cubit = context
        .read<OtherMaterialInwardCubit>();

    final bool succeeded = await cubit.createLot(
      partyId: _party!.id,
      recipePublicId: _recipe!.publicId,
      quantity: _quantityController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.OTHER_INWARD_CREATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.inventory_2_outlined,
      title: AppStrings.ADD_OTHER_INWARD,
      subtitle: AppStrings.ADD_OTHER_INWARD_SUBTITLE,
      submitLabel: AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            RecipePickerField(
              value: _recipe,
              recipes: RecipesService.instance.recipes,
              enabled: !_isSubmitting,
              errorText: _recipeError,
              onSelected: (recipe) => setState(() {
                _recipe = recipe;
                _recipeError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            PartyPickerField(
              value: _party,
              parties: PartiesService.instance.parties,
              enabled: !_isSubmitting,
              errorText: _partyError,
              onSelected: (party) => setState(() {
                _party = party;
                _partyError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _quantityController,
              label: _quantityLabel,
              hint: AppStrings.FIELD_RECIPE_QUANTITY_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
              ],
              validator: FormValidators.positiveAmount,
            ),
          ],
        ),
      ),
    );
  }
}
