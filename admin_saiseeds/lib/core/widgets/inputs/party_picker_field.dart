import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/parties/data/models/party_model.dart';
import 'searchable_field.dart';

class PartyPickerField extends StatelessWidget {
  final PartyModel? value;
  final List<PartyModel> parties;
  final ValueChanged<PartyModel> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const PartyPickerField({
    super.key,
    required this.value,
    required this.parties,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
  });

  static String label(PartyModel party) => party.name;

  static String searchText(PartyModel party) =>
      '${party.name} ${party.cityName}';

  @override
  Widget build(BuildContext context) {
    return SearchableField<PartyModel>(
      label: AppStrings.FIELD_PARTY,
      hintText: AppStrings.FIELD_PARTY_HINT,
      value: value,
      items: parties,
      itemToString: label,
      searchText: searchText,
      isSame: (a, b) => a.id == b.id,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
    );
  }
}
