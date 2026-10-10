import '../data/models/export_kind.dart';

/// A flattened report: one header row plus the data rows beneath it.
class ExportSheet {
  final List<String> headers;
  final List<List<String>> rows;

  /// Column whose repeated value marks rows belonging to one record -- the
  /// order id, the challan's order id, the snapshot's day. Rows for one
  /// record are always written consecutively, so a change in this column is
  /// where one record ends and the next begins.
  final int groupColumn;

  /// How many leading columns describe the parent record rather than the
  /// line. On a record's second and later rows these repeat, so they are
  /// blanked: the order reads as one block instead of several identical
  /// ones. Zero leaves every row complete.
  final int headSpan;

  const ExportSheet({
    required this.headers,
    required this.rows,
    this.groupColumn = 0,
    this.headSpan = 0,
  });

  bool get isEmpty => rows.isEmpty;

  /// The rows as written: a continuation row drops its repeated parent
  /// columns so the eye groups it with the line above.
  List<List<String>> get displayRows {
    if (headSpan <= 0) return rows;

    final List<int> groups = groupIndices;
    final List<List<String>> out = [];

    for (int i = 0; i < rows.length; i++) {
      if (i == 0 || groups[i] != groups[i - 1]) {
        out.add(rows[i]);
        continue;
      }
      final List<String> row = [...rows[i]];
      for (int c = 0; c < headSpan && c < row.length; c++) {
        row[c] = '';
      }
      out.add(row);
    }

    return out;
  }

  /// Index of each row's record, counting from zero. Lets the writer shade
  /// alternate records so a multi-line one reads as a single block.
  List<int> get groupIndices {
    final List<int> indices = [];
    String? previous;
    int group = -1;

    for (final List<String> row in rows) {
      final String key = groupColumn < row.length ? row[groupColumn] : '';
      if (key != previous) {
        group++;
        previous = key;
      }
      indices.add(group);
    }

    return indices;
  }
}

/// Turns an export payload into rows for a spreadsheet.
///
/// Every report is flattened to its most granular line -- an order row per
/// item, a challan row per item, an inward row per entry -- because a
/// spreadsheet is read and pivoted per line, and repeating the parent
/// columns is what makes that possible.
class ExportSheets {
  ExportSheets._();

  static ExportSheet build(ExportKind kind, Map<String, dynamic> payload) {
    final List<Map<String, dynamic>> results = _listOf(payload['results']);

    switch (kind) {
      case ExportKind.orders:
        return _orders(results);
      case ExportKind.customOrders:
        return _customOrders(results);
      case ExportKind.dispatchReceipts:
        return _dispatchReceipts(results);
      case ExportKind.inwardEntries:
        return _inwardEntries(results);
      case ExportKind.inventorySnapshots:
        return _inventorySnapshots(results);
      case ExportKind.labTestings:
        throw UnsupportedError(
          'Lab testing reports are a PDF document, not a spreadsheet -- see '
          'ExportsCubit.export, which never reaches this branch for them.',
        );
    }
  }

  // ─────────────────────────── orders ───────────────────────────

  static ExportSheet _orders(List<Map<String, dynamic>> results) {
    const List<String> headers = [
      'Order ID',
      'Booked On',
      'Client',
      'Client GST',
      'City',
      'Delivery Address',
      'Status',
      'Dispatch Mode',
      'Transport Agency',
      'Expected Delivery',
      'Actual Delivery',
      'Verified At',
      'Special Comments',
      'Product',
      'Packet Weight (kg)',
      'Packets / Bag',
      'Total Weight (kg)',
      'List Price',
      'Negotiated Price',
      'Bags',
      'Line Total',
      'Order Total',
      'Order Packets',
    ];

    final List<List<String>> rows = [];

    for (final Map<String, dynamic> order in results) {
      final Map<String, dynamic> client = _mapOf(order['client']);
      final List<String> head = [
        _text(order['public_id']),
        _date(order['created_at']),
        _text(client['company_name']),
        _text(client['gst_number']),
        _text(_mapOf(order['city'])['name']),
        _text(order['delivery_address']),
        _text(order['status']),
        _text(order['dispatch_mode']),
        _text(_mapOf(order['transport_agency'])['name']),
        _text(order['expected_delivery_date']),
        _text(order['actual_delivery_date']),
        _date(order['verified_at']),
        _text(order['special_comments']),
      ];
      final List<String> tail = [
        _text(order['total_amount']),
        _text(order['total_packets']),
      ];

      final List<Map<String, dynamic>> items = _listOf(order['items']);
      if (items.isEmpty) {
        rows.add([...head, ...List.filled(8, ''), ...tail]);
        continue;
      }

      for (final Map<String, dynamic> item in items) {
        final Map<String, dynamic> packaging = _mapOf(item['packaging']);
        rows.add([
          ...head,
          _text(_mapOf(packaging['product'])['name']),
          _text(packaging['packet_weight']),
          _text(packaging['packets']),
          _text(packaging['total_weight']),
          _text(packaging['selling_price']),
          _text(item['negotiated_selling_price']),
          _text(item['quantity']),
          _text(item['line_total']),
          ...tail,
        ]);
      }
    }

    return ExportSheet(headers: headers, rows: rows, headSpan: 13);
  }

  // ──────────────────────── custom orders ───────────────────────

  static ExportSheet _customOrders(List<Map<String, dynamic>> results) {
    const List<String> headers = [
      'Order ID',
      'Booked On',
      'Client',
      'Client GST',
      'City',
      'Delivery Address',
      'Status',
      'Expected Delivery',
      'Actual Delivery',
      'Verified At',
      'Special Comments',
      'Product',
      'Packet Weight (kg)',
      'Negotiated Price',
      'Packets',
      'Line Total',
      'Order Total',
      'Order Packets',
    ];

    final List<List<String>> rows = [];

    for (final Map<String, dynamic> order in results) {
      final Map<String, dynamic> client = _mapOf(order['client']);
      final List<String> head = [
        _text(order['public_id']),
        _date(order['created_at']),
        _text(client['company_name']),
        _text(client['gst_number']),
        _text(_mapOf(order['city'])['name']),
        _text(order['delivery_address']),
        _text(order['status']),
        _text(order['expected_delivery_date']),
        _text(order['actual_delivery_date']),
        _date(order['verified_at']),
        _text(order['special_comments']),
      ];
      final List<String> tail = [
        _text(order['total_amount']),
        _text(order['total_packets']),
      ];

      final List<Map<String, dynamic>> items = _listOf(order['items']);
      if (items.isEmpty) {
        rows.add([...head, ...List.filled(5, ''), ...tail]);
        continue;
      }

      for (final Map<String, dynamic> item in items) {
        rows.add([
          ...head,
          _text(_mapOf(item['product'])['name']),
          _text(item['packet_weight']),
          _text(item['negotiated_selling_price']),
          _text(item['packets']),
          _text(item['line_total']),
          ...tail,
        ]);
      }
    }

    return ExportSheet(headers: headers, rows: rows, headSpan: 11);
  }

  // ─────────────────────── dispatch receipts ────────────────────

  static ExportSheet _dispatchReceipts(List<Map<String, dynamic>> results) {
    const List<String> headers = [
      'Order ID',
      'Order Type',
      'Booked On',
      'Challan Number',
      'Dispatch ID',
      'LR Number',
      'Dispatch Date',
      'Transport',
      'Vehicle',
      'Driver',
      'Driver Number',
      'From City',
      'To City',
      'Receiver',
      'Receiver GST',
      'Receiver Address',
      'Contact Person',
      'Contact Number',
      'HSN Code',
      'Financial Year',
      'Product',
      'Packet Weight (kg)',
      'Packets / Bag',
      'Bags',
      'Total Weight (kg)',
      'Lot Number',
      'Negotiated Price',
      'Line Total',
      'Items',
      'Total Amount',
      'Total Packets',
    ];

    final List<List<String>> rows = [];

    for (final Map<String, dynamic> challan in results) {
      final Map<String, dynamic> dispatch = _mapOf(challan['dispatch']);
      final Map<String, dynamic> receiver = _mapOf(challan['receiver_details']);
      final Map<String, dynamic> address = _mapOf(receiver['address']);

      final List<String> head = [
        _text(challan['order_public_id']),
        _text(challan['order_type'], fallback: 'ORDER'),
        _date(challan['order_created_at']),
        _text(dispatch['challan_number']),
        _text(dispatch['public_id']),
        _text(dispatch['lr_number']),
        _text(dispatch['dispatch_date']),
        _transport(dispatch),
        _text(dispatch['vehicle_number']),
        _text(dispatch['driver_name']),
        _text(dispatch['driver_number']),
        _text(dispatch['from_city']),
        _text(dispatch['to_city']),
        _text(receiver['company_name']),
        _text(receiver['gst_number']),
        _address(address),
        _text(receiver['contact_person_name']),
        _text(receiver['contact_person_number']),
        _text(challan['hsn_code']),
        _text(challan['financial_year']),
      ];
      final List<String> tail = [
        _text(challan['item_count']),
        _text(challan['total_amount']),
        _text(challan['total_packets']),
      ];

      final List<Map<String, dynamic>> items = _listOf(challan['items']);
      if (items.isEmpty) {
        rows.add([...head, ...List.filled(8, ''), ...tail]);
        continue;
      }

      for (final Map<String, dynamic> item in items) {
        rows.add([
          ...head,
          _text(_mapOf(item['product'])['name']),
          _text(item['packet_weight']),
          _text(item['packets']),
          // A custom order line has no bag count; it is loose packets.
          _text(item['quantity']),
          _text(item['total_weight']),
          _text(item['lot_number']),
          _text(item['negotiated_selling_price']),
          _text(item['line_total']),
          ...tail,
        ]);
      }
    }

    return ExportSheet(headers: headers, rows: rows, headSpan: 20);
  }

  // ───────────────────────── inward entries ─────────────────────

  static ExportSheet _inwardEntries(List<Map<String, dynamic>> results) {
    const List<String> headers = [
      'Date',
      'Entry Type',
      'Entry ID',
      'Product',
      'Material Type',
      'Party',
      'Lot Number',
      'Quantity',
      'Packet Weight (kg)',
      'Status',
      'Lab Sampling Date',
      'Effective Date',
      'Recorded At',
    ];

    final List<List<String>> rows = [];

    for (final Map<String, dynamic> day in results) {
      final String date = _text(day['date']);

      for (final Map<String, dynamic> raw in _listOf(day['raw_materials'])) {
        rows.add([
          date,
          'Raw Material',
          _text(raw['public_id']),
          _text(_mapOf(raw['product'])['name']),
          '',
          _text(_mapOf(raw['party'])['name']),
          _text(raw['lot_no']),
          _text(raw['quantity_kg']),
          '',
          _text(raw['status']),
          _text(raw['lab_sampling_date']),
          _text(raw['effective_date']),
          _date(raw['created_at']),
        ]);
      }

      for (final Map<String, dynamic> other in _listOf(
        day['other_materials'],
      )) {
        final Map<String, dynamic> recipe = _mapOf(other['recipe']);
        rows.add([
          date,
          'Other Material',
          _text(other['public_id']),
          _text(_mapOf(recipe['product'])['name']),
          _text(_mapOf(recipe['material_type'])['name']),
          _text(_mapOf(other['party'])['name']),
          '',
          _text(other['quantity']),
          _text(recipe['packet_weight']),
          '',
          '',
          _text(other['effective_date']),
          _date(other['created_at']),
        ]);
      }
    }

    return ExportSheet(headers: headers, rows: rows, headSpan: 1);
  }

  // ─────────────────────── inventory snapshots ──────────────────

  static ExportSheet _inventorySnapshots(List<Map<String, dynamic>> results) {
    const List<String> headers = [
      'Snapshot Date',
      'Kind',
      'Entry ID',
      'Product',
      'Packet Weight (kg)',
      'Packets / Bag',
      'Bags',
      'Packets',
      'Total Weight (kg)',
    ];

    final List<List<String>> rows = [];

    for (final Map<String, dynamic> row in results) {
      final bool isBag = '${row['kind']}'.toLowerCase() == 'bag';
      // A bag row nests its product under packaging; a loose row carries
      // the product and weight directly.
      final Map<String, dynamic> packaging = _mapOf(row['packaging']);
      final Map<String, dynamic> product = isBag
          ? _mapOf(packaging['product'])
          : _mapOf(row['product']);

      rows.add([
        _text(row['snapshot_date']),
        isBag ? 'Bag' : 'Loose',
        _text(row['public_id']),
        _text(product['name']),
        _text(isBag ? packaging['packet_weight'] : row['packet_weight']),
        isBag ? _text(packaging['packets']) : '',
        isBag ? _text(row['bags']) : '',
        _text(isBag ? row['total_packets'] : row['packets']),
        _text(row['total_weight']),
      ]);
    }

    return ExportSheet(headers: headers, rows: rows);
  }

  // ───────────────────────────── helpers ────────────────────────

  static String _transport(Map<String, dynamic> dispatch) {
    if (dispatch['is_private'] == true) return 'Private';
    final String agency = _text(_mapOf(dispatch['transport_agency'])['name']);
    return agency.isEmpty ? 'Agency' : agency;
  }

  static String _address(Map<String, dynamic> address) {
    return [
          address['line_1'],
          address['line_2'],
          address['city'],
          address['state'],
          address['pincode'],
          address['country'],
        ]
        .map((part) => '${part ?? ''}'.trim())
        .where((p) => p.isNotEmpty)
        .join(', ');
  }

  /// Dates are written as "YYYY-MM-DD HH:MM" so a spreadsheet sorts them in
  /// chronological order rather than alphabetically on an ISO string.
  static String _date(dynamic value) {
    final String raw = '${value ?? ''}'.trim();
    if (raw.isEmpty) return '';
    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    final DateTime local = parsed.toLocal();
    return '${local.year.toString().padLeft(4, '0')}-'
        '${local.month.toString().padLeft(2, '0')}-'
        '${local.day.toString().padLeft(2, '0')} '
        '${local.hour.toString().padLeft(2, '0')}:'
        '${local.minute.toString().padLeft(2, '0')}';
  }

  static String _text(dynamic value, {String fallback = ''}) {
    if (value == null) return fallback;
    final String raw = '$value'.trim();
    return raw.isEmpty ? fallback : raw;
  }

  static Map<String, dynamic> _mapOf(dynamic value) =>
      value is Map ? Map<String, dynamic>.from(value) : const {};

  static List<Map<String, dynamic>> _listOf(dynamic value) => value is List
      ? value
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList()
      : const [];
}
