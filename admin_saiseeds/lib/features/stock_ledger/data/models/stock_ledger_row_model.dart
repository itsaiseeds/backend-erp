/// The four pool kinds the ledger tracks, in the same order the backend
/// lists them -- each event row carries the full state of every pool, not
/// only the ones it touched.
library;

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}

String _asStr(dynamic value) => value == null ? '' : '$value';

num _asNum(String decimal) => num.tryParse(decimal) ?? 0;

/// `on_hand` / `reserved` / `consumed` / `available`, shared by a bag or a
/// loose-packet pool's live figures and its `change` sub-object alike.
class LedgerCountChange {
  final int onHand;
  final int reserved;
  final int consumed;
  final int available;

  const LedgerCountChange({
    this.onHand = 0,
    this.reserved = 0,
    this.consumed = 0,
    this.available = 0,
  });

  factory LedgerCountChange.fromJson(Map<String, dynamic> json) {
    return LedgerCountChange(
      onHand: _asInt(json['on_hand']),
      reserved: _asInt(json['reserved']),
      consumed: _asInt(json['consumed']),
      available: _asInt(json['available']),
    );
  }

  bool get isZero =>
      onHand == 0 && reserved == 0 && consumed == 0 && available == 0;
}

class LedgerPackagingRef {
  final String publicId;
  final String packetWeight;
  final int packets;

  const LedgerPackagingRef({
    this.publicId = '',
    this.packetWeight = '',
    this.packets = 0,
  });

  factory LedgerPackagingRef.fromJson(Map<String, dynamic> json) {
    return LedgerPackagingRef(
      publicId: _asStr(json['public_id']),
      packetWeight: _asStr(json['packet_weight']),
      packets: _asInt(json['packets']),
    );
  }

  num get packetWeightValue => _asNum(packetWeight);
}

/// One `ProductPackaging`'s bag pool -- on hand, reserved, consumed and
/// available bags, plus what this event changed.
class LedgerBagPool {
  final LedgerPackagingRef packaging;
  final LedgerCountChange figures;
  final LedgerCountChange change;

  const LedgerBagPool({
    required this.packaging,
    required this.figures,
    required this.change,
  });

  factory LedgerBagPool.fromJson(Map<String, dynamic> json) {
    final dynamic packaging = json['packaging'];
    return LedgerBagPool(
      packaging: packaging is Map
          ? LedgerPackagingRef.fromJson(Map<String, dynamic>.from(packaging))
          : const LedgerPackagingRef(),
      figures: LedgerCountChange.fromJson(json),
      change: json['change'] is Map
          ? LedgerCountChange.fromJson(Map<String, dynamic>.from(json['change']))
          : const LedgerCountChange(),
    );
  }

  /// Identifies this pool across rows, for the chain's "which pools exist on
  /// this product" summary and for diffing two rows' states.
  String get key => 'bag:${packaging.publicId}';
}

/// One `(product, packet_weight)` loose pool.
class LedgerPacketPool {
  final String packetWeight;
  final LedgerCountChange figures;
  final LedgerCountChange change;

  const LedgerPacketPool({
    required this.packetWeight,
    required this.figures,
    required this.change,
  });

  factory LedgerPacketPool.fromJson(Map<String, dynamic> json) {
    return LedgerPacketPool(
      packetWeight: _asStr(json['packet_weight']),
      figures: LedgerCountChange.fromJson(json),
      change: json['change'] is Map
          ? LedgerCountChange.fromJson(Map<String, dynamic>.from(json['change']))
          : const LedgerCountChange(),
    );
  }

  num get packetWeightValue => _asNum(packetWeight);

  String get key => 'loose:$packetWeight';
}

/// `incoming` / `packed` / `rejected` / `wasted` / `available`, in kilograms
/// (3-dp decimal strings over the wire).
class LedgerRawFigures {
  final String incoming;
  final String packed;
  final String rejected;
  final String wasted;
  final String available;

  const LedgerRawFigures({
    this.incoming = '0.000',
    this.packed = '0.000',
    this.rejected = '0.000',
    this.wasted = '0.000',
    this.available = '0.000',
  });

  factory LedgerRawFigures.fromJson(Map<String, dynamic> json) {
    return LedgerRawFigures(
      incoming: _asStr(json['incoming']),
      packed: _asStr(json['packed']),
      rejected: _asStr(json['rejected']),
      wasted: _asStr(json['wasted']),
      available: _asStr(json['available']),
    );
  }

  num get incomingValue => _asNum(incoming);

  num get packedValue => _asNum(packed);

  num get rejectedValue => _asNum(rejected);

  num get wastedValue => _asNum(wasted);

  num get availableValue => _asNum(available);

  bool get isZero =>
      incomingValue == 0 &&
      packedValue == 0 &&
      rejectedValue == 0 &&
      wastedValue == 0 &&
      availableValue == 0;
}

class LedgerRawMaterial {
  final LedgerRawFigures figures;
  final LedgerRawFigures change;

  const LedgerRawMaterial({required this.figures, required this.change});

  factory LedgerRawMaterial.fromJson(Map<String, dynamic> json) {
    return LedgerRawMaterial(
      figures: LedgerRawFigures.fromJson(json),
      change: json['change'] is Map
          ? LedgerRawFigures.fromJson(Map<String, dynamic>.from(json['change']))
          : const LedgerRawFigures(),
    );
  }
}

class LedgerMaterialTypeRef {
  final int id;
  final String name;
  final String unitType;

  const LedgerMaterialTypeRef({this.id = 0, this.name = '', this.unitType = ''});

  factory LedgerMaterialTypeRef.fromJson(Map<String, dynamic> json) {
    return LedgerMaterialTypeRef(
      id: _asInt(json['id']),
      name: _asStr(json['name']),
      unitType: _asStr(json['unit_type']),
    );
  }
}

/// `incoming` / `packed` / `available`, in the material type's own unit --
/// `used_by_other_products` is not part of the wire shape the UI needs
/// directly; it is implied by `incoming - packed - available`.
class LedgerOtherFigures {
  final String incoming;
  final String packed;
  final String available;

  const LedgerOtherFigures({
    this.incoming = '0.000',
    this.packed = '0.000',
    this.available = '0.000',
  });

  factory LedgerOtherFigures.fromJson(Map<String, dynamic> json) {
    return LedgerOtherFigures(
      incoming: _asStr(json['incoming']),
      packed: _asStr(json['packed']),
      available: _asStr(json['available']),
    );
  }

  num get incomingValue => _asNum(incoming);

  num get packedValue => _asNum(packed);

  num get availableValue => _asNum(available);

  bool get isZero =>
      incomingValue == 0 && packedValue == 0 && availableValue == 0;
}

class LedgerOtherMaterial {
  final LedgerMaterialTypeRef materialType;
  final String packetWeight;
  final LedgerOtherFigures figures;
  final LedgerOtherFigures change;

  const LedgerOtherMaterial({
    required this.materialType,
    this.packetWeight = '',
    required this.figures,
    required this.change,
  });

  factory LedgerOtherMaterial.fromJson(Map<String, dynamic> json) {
    final dynamic materialType = json['material_type'];
    return LedgerOtherMaterial(
      materialType: materialType is Map
          ? LedgerMaterialTypeRef.fromJson(Map<String, dynamic>.from(materialType))
          : const LedgerMaterialTypeRef(),
      packetWeight: _asStr(json['packet_weight']),
      figures: LedgerOtherFigures.fromJson(json),
      change: json['change'] is Map
          ? LedgerOtherFigures.fromJson(Map<String, dynamic>.from(json['change']))
          : const LedgerOtherFigures(),
    );
  }

  String get key => 'other:${materialType.id}';
}

class LedgerSourceRef {
  final String kind;
  final String publicId;
  final String label;

  const LedgerSourceRef({this.kind = '', this.publicId = '', this.label = ''});

  factory LedgerSourceRef.fromJson(Map<String, dynamic> json) {
    return LedgerSourceRef(
      kind: _asStr(json['kind']),
      publicId: _asStr(json['public_id']),
      label: _asStr(json['label']),
    );
  }
}

class LedgerActorRef {
  final int id;
  final String name;

  const LedgerActorRef({this.id = 0, this.name = ''});

  factory LedgerActorRef.fromJson(Map<String, dynamic> json) {
    return LedgerActorRef(id: _asInt(json['id']), name: _asStr(json['name']));
  }
}

/// One row of the ledger: a synthetic `OPENING_BALANCE` / `CLOSING_BALANCE`,
/// or a real stock event. Every row carries the full state of every pool the
/// product has, plus the `change` this event made to it.
class StockLedgerRow {
  final String event;
  final String? detail;
  final String occurredAt;
  final LedgerSourceRef? source;
  final LedgerActorRef? actor;
  final List<LedgerBagPool> bagPools;
  final List<LedgerPacketPool> packetPools;
  final LedgerRawMaterial rawMaterial;
  final List<LedgerOtherMaterial> otherMaterials;

  const StockLedgerRow({
    required this.event,
    this.detail,
    this.occurredAt = '',
    this.source,
    this.actor,
    this.bagPools = const [],
    this.packetPools = const [],
    required this.rawMaterial,
    this.otherMaterials = const [],
  });

  factory StockLedgerRow.fromJson(Map<String, dynamic> json) {
    final dynamic source = json['source'];
    final dynamic actor = json['actor'];
    final dynamic bagPools = json['bag_pools'];
    final dynamic packetPools = json['packet_pools'];
    final dynamic otherMaterials = json['other_materials'];
    final dynamic rawMaterial = json['raw_material'];

    return StockLedgerRow(
      event: _asStr(json['event']),
      detail: json['detail'] == null ? null : _asStr(json['detail']),
      occurredAt: _asStr(json['occurred_at']),
      source: source is Map
          ? LedgerSourceRef.fromJson(Map<String, dynamic>.from(source))
          : null,
      actor: actor is Map
          ? LedgerActorRef.fromJson(Map<String, dynamic>.from(actor))
          : null,
      bagPools: bagPools is List
          ? bagPools
                .whereType<Map>()
                .map((e) => LedgerBagPool.fromJson(Map<String, dynamic>.from(e)))
                .toList()
          : const [],
      packetPools: packetPools is List
          ? packetPools
                .whereType<Map>()
                .map((e) => LedgerPacketPool.fromJson(Map<String, dynamic>.from(e)))
                .toList()
          : const [],
      rawMaterial: rawMaterial is Map
          ? LedgerRawMaterial.fromJson(Map<String, dynamic>.from(rawMaterial))
          : LedgerRawMaterial(
              figures: const LedgerRawFigures(),
              change: const LedgerRawFigures(),
            ),
      otherMaterials: otherMaterials is List
          ? otherMaterials
                .whereType<Map>()
                .map(
                  (e) => LedgerOtherMaterial.fromJson(Map<String, dynamic>.from(e)),
                )
                .toList()
          : const [],
    );
  }

  bool get isOpening => event == 'OPENING_BALANCE';

  bool get isClosing => event == 'CLOSING_BALANCE';

  bool get isBalance => isOpening || isClosing;

  DateTime? get occurredAtTime => DateTime.tryParse(occurredAt);

  /// Whether anything at all changed on this row -- always true for a real
  /// event (the backend never writes a no-op row) and meaningless for a
  /// balance row, which has no `change` to speak of.
  bool get hasAnyChange {
    if (isBalance) return true;
    if (bagPools.any((p) => !p.change.isZero)) return true;
    if (packetPools.any((p) => !p.change.isZero)) return true;
    if (!rawMaterial.change.isZero) return true;
    if (otherMaterials.any((m) => !m.change.isZero)) return true;
    return false;
  }
}
