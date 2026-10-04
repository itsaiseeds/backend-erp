import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../data/models/field_trip_model.dart';
import '../bloc/field_trips_cubit.dart';

const int _VILLAGE_MAX_LENGTH = 120;

/// Edits a trip's plan. The admin endpoint accepts a PATCH only while the
/// trip is still PLANNED, so the caller must gate on [FieldTripModel.canEdit].
class FieldTripFormDialog extends StatefulWidget {
  final FieldTripModel trip;

  const FieldTripFormDialog({super.key, required this.trip});

  static Future<void> show(
    BuildContext context, {
    required FieldTripsCubit cubit,
    required FieldTripModel trip,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<FieldTripsCubit>.value(
        value: cubit,
        child: FieldTripFormDialog(trip: trip),
      ),
    );
  }

  @override
  State<FieldTripFormDialog> createState() => _FieldTripFormDialogState();
}

class _FieldTripFormDialogState extends State<FieldTripFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _villageController = TextEditingController();

  CityModel? _city;
  DateTime? _expectedStart;
  DateTime? _expectedEnd;

  bool _isSubmitting = false;
  String? _cityError;
  String? _startError;
  String? _endError;

  @override
  void initState() {
    super.initState();
    _villageController.text = widget.trip.village;
    _city = MetadataService.instance.cityById(widget.trip.cityId);
    _expectedStart = widget.trip.expectedStartDateTime;
    _expectedEnd = widget.trip.expectedEndDateTime;
  }

  @override
  void dispose() {
    _villageController.dispose();
    super.dispose();
  }

  /// A new day keeps the time the trip was already planned for, so editing
  /// the date never silently moves a trip to midnight.
  static DateTime _withTimeOf(DateTime day, DateTime? original) {
    if (original == null) return day;
    return DateTime(
      day.year,
      day.month,
      day.day,
      original.hour,
      original.minute,
      original.second,
    );
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final DateTime? start = _expectedStart;
    final DateTime? end = _expectedEnd;

    final bool isCityValid = _city != null;
    final bool isStartValid = start != null;
    final bool isEndValid = end != null;
    final bool isOrderValid =
        !isStartValid || !isEndValid || !end.isBefore(start);

    setState(() {
      _cityError = isCityValid ? null : AppStrings.VALIDATION_CITY_REQUIRED;
      _startError = isStartValid
          ? null
          : AppStrings.VALIDATION_EXPECTED_START_REQUIRED;
      _endError = !isEndValid
          ? AppStrings.VALIDATION_EXPECTED_END_REQUIRED
          : (isOrderValid
                ? null
                : AppStrings.VALIDATION_EXPECTED_END_BEFORE_START);
    });

    if (!isFormValid ||
        !isCityValid ||
        !isStartValid ||
        !isEndValid ||
        !isOrderValid) {
      return;
    }

    setState(() => _isSubmitting = true);
    final FieldTripsCubit cubit = context.read<FieldTripsCubit>();

    final bool succeeded = await cubit.updateTrip(
      publicId: widget.trip.publicId,
      cityId: _city!.id,
      village: _villageController.text.trim(),
      expectedStartAt: start.toIso8601String(),
      expectedEndAt: end.toIso8601String(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.FIELD_TRIP_UPDATED_TITLE);
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
      icon: Icons.map_outlined,
      title: AppStrings.EDIT_FIELD_TRIP,
      subtitle: AppStrings.EDIT_FIELD_TRIP_SUBTITLE,
      submitLabel: AppStrings.UPDATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            CityPickerField(
              value: _city,
              enabled: !_isSubmitting,
              errorText: _cityError,
              onSelected: (city) => setState(() {
                _city = city;
                _cityError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _villageController,
              label: AppStrings.FIELD_VILLAGE,
              hint: AppStrings.FIELD_VILLAGE_HINT,
              enabled: !_isSubmitting,
              inputFormatters: [
                LengthLimitingTextInputFormatter(_VILLAGE_MAX_LENGTH),
              ],
              validator: FormValidators.requiredField,
            ),
            const SizedBox(height: AppSpacing.md),
            SingleDateField(
              label: AppStrings.FIELD_EXPECTED_START,
              value: _expectedStart,
              enabled: !_isSubmitting,
              onChanged: (date) => setState(() {
                _expectedStart = date == null
                    ? null
                    : _withTimeOf(date, _expectedStart);
                _startError = null;
              }),
            ),
            if (_startError != null) _buildFieldError(context, _startError!),
            const SizedBox(height: AppSpacing.md),
            SingleDateField(
              label: AppStrings.FIELD_EXPECTED_END,
              value: _expectedEnd,
              enabled: !_isSubmitting,
              onChanged: (date) => setState(() {
                _expectedEnd = date == null
                    ? null
                    : _withTimeOf(date, _expectedEnd);
                _endError = null;
              }),
            ),
            if (_endError != null) _buildFieldError(context, _endError!),
          ],
        ),
      ),
    );
  }

  Widget _buildFieldError(BuildContext context, String message) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Text(
        message,
        style: Theme.of(context).inputDecorationTheme.errorStyle,
      ),
    );
  }
}
