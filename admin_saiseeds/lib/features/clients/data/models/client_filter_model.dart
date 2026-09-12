enum ClientFilterKind { select, text, datetimeRange, unsupported }

class ClientFilterOption {
  final String value;
  final String label;

  const ClientFilterOption({required this.value, required this.label});

  factory ClientFilterOption.fromJson(Map<String, dynamic> json) {
    final dynamic raw = json['value'];
    return ClientFilterOption(
      value: raw == null ? '' : '$raw',
      label: json['label'] as String? ?? '',
    );
  }
}

class ClientFilterModel {
  final String key;
  final String label;
  final ClientFilterKind kind;
  final String description;
  final List<ClientFilterOption> options;
  final List<String> params;

  const ClientFilterModel({
    required this.key,
    this.label = '',
    required this.kind,
    this.description = '',
    this.options = const [],
    this.params = const [],
  });

  factory ClientFilterModel.fromJson(Map<String, dynamic> json) {
    return ClientFilterModel(
      key: json['filter'] as String? ?? '',
      label: json['label'] as String? ?? '',
      kind: _kindFrom(json['kind'] as String? ?? ''),
      description: json['description'] as String? ?? '',
      options: json['options'] is List
          ? (json['options'] as List)
                .whereType<Map>()
                .map(
                  (entry) => ClientFilterOption.fromJson(
                    Map<String, dynamic>.from(entry),
                  ),
                )
                .toList()
          : const [],
      params: json['params'] is List
          ? (json['params'] as List).map((p) => '$p').toList()
          : const [],
    );
  }

  static ClientFilterKind _kindFrom(String raw) {
    switch (raw) {
      case 'select':
        return ClientFilterKind.select;
      case 'text':
        return ClientFilterKind.text;
      case 'datetime_range':
        return ClientFilterKind.datetimeRange;
      default:
        return ClientFilterKind.unsupported;
    }
  }

  String get displayLabel => label.isNotEmpty ? label : key;

  bool get isSelect => kind == ClientFilterKind.select;

  String get lowerBoundParam => params.isNotEmpty ? params.first : '${key}_gte';

  String get upperBoundParam => params.length > 1 ? params[1] : '${key}_lte';

  String labelForValue(String value) {
    for (final option in options) {
      if (option.value == value) return option.label;
    }
    return value;
  }
}

class ClientSortModel {
  final String key;
  final String label;
  final String description;

  const ClientSortModel({
    required this.key,
    this.label = '',
    this.description = '',
  });

  factory ClientSortModel.fromJson(Map<String, dynamic> json) {
    return ClientSortModel(
      key: json['sort'] as String? ?? '',
      label: json['label'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }

  String get displayLabel => label.isNotEmpty ? label : key;
}
