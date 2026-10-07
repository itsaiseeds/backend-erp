import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/dispatch_challans/data/models/dispatch_lot_number_model.dart';
import 'searchable_field.dart';

class LotNumberPickerField extends StatelessWidget {
  final DispatchLotNumberModel? value;
  final String productPackagingName;

  /// The product this line is for -- the API returns recent lots across
  /// every product, so this picker only offers the ones that match.
  final String productName;
  final List<DispatchLotNumberModel> lotNumbers;
  final ValueChanged<DispatchLotNumberModel> onSelected;
  final ValueChanged<String> onFreeEntry;
  final bool enabled;
  final String? errorText;
  final bool isUnavailable;

  const LotNumberPickerField({
    super.key,
    required this.value,
    required this.productPackagingName,
    required this.productName,
    required this.lotNumbers,
    required this.onSelected,
    required this.onFreeEntry,
    this.enabled = true,
    this.errorText,
    this.isUnavailable = false,
  });

  static String label(DispatchLotNumberModel lot) => lot.lotNumber;

  static String searchText(DispatchLotNumberModel lot) => lot.lotNumber;

  List<DispatchLotNumberModel> get _productLots {
    final String needle = productName.trim().toLowerCase();
    if (needle.isEmpty) return lotNumbers;
    return lotNumbers
        .where((lot) => lot.productName.trim().toLowerCase() == needle)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return SearchableField<DispatchLotNumberModel>(
      label: "${AppStrings.FIELD_LOT_NUMBER} : $productPackagingName",
      hintText: AppStrings.FIELD_LOT_NUMBER_RECENT_HINT,
      value: value,
      items: _productLots,
      itemToString: label,
      searchText: searchText,
      isSame: (a, b) => a.lotNumber == b.lotNumber,
      onSelected: onSelected,
      onFreeEntry: onFreeEntry,
      allowFreeEntry: true,
      errorText: errorText,
      enabled: enabled,
      helperText: isUnavailable ? AppStrings.LOT_NUMBERS_UNAVAILABLE : null,
      emptyHint: AppStrings.LOT_NUMBERS_UNAVAILABLE,
    );
  }
}
