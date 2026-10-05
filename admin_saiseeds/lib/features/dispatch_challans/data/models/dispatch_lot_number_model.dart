class DispatchLotNumberModel {
  final String lotNumber;
  final String lastUsedAt;

  const DispatchLotNumberModel({required this.lotNumber, this.lastUsedAt = ''});

  factory DispatchLotNumberModel.fromJson(Map<String, dynamic> json) {
    return DispatchLotNumberModel(
      lotNumber: '${json['lot_number'] ?? ''}',
      lastUsedAt: _textOf(json['last_used_at']),
    );
  }

  static String _textOf(dynamic value) {
    if (value == null) return '';
    return '$value';
  }
}
