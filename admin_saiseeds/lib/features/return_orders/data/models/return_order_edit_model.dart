import 'return_order_model.dart';

/// One editable line of a return.
///
/// The admin edits by **replacement**, so the request carries the whole return
/// every time -- a line left out of [ReturnOrderEditRequest.items] is deleted.
/// That is why this carries the line's identity rather than a diff.
class ReturnOrderItemEditModel {
  final ReturnProductRefModel product;
  final num packetWeight;
  final int packets;
  final num pricePerPacket;

  const ReturnOrderItemEditModel({
    this.product = const ReturnProductRefModel(),
    this.packetWeight = 0,
    this.packets = 0,
    this.pricePerPacket = 0,
  });

  factory ReturnOrderItemEditModel.fromItem(ReturnOrderItemModel item) {
    return ReturnOrderItemEditModel(
      product: item.product,
      packetWeight: item.packetWeight,
      packets: item.packets,
      pricePerPacket: item.pricePerPacket,
    );
  }

  static const int WEIGHT_DECIMALS = 3;
  static const int PRICE_DECIMALS = 2;

  Map<String, dynamic> toJson() => {
    'product_public_id': product.publicId,
    'packet_weight': packetWeight.toStringAsFixed(WEIGHT_DECIMALS),
    'packets': packets,
    'price_per_packet': pricePerPacket.toStringAsFixed(PRICE_DECIMALS),
  };

  ReturnOrderItemEditModel copyWith({int? packets, num? pricePerPacket}) {
    return ReturnOrderItemEditModel(
      product: product,
      packetWeight: packetWeight,
      packets: packets ?? this.packets,
      pricePerPacket: pricePerPacket ?? this.pricePerPacket,
    );
  }

  num get kg => packetWeight * packets;

  num get lineTotal => pricePerPacket * packets;
}

class ReturnOrderEditRequest {
  final DateTime? returnDate;
  final List<ReturnOrderItemEditModel> items;

  const ReturnOrderEditRequest({this.returnDate, required this.items});

  /// Seeds the editor with the return as it stands.
  factory ReturnOrderEditRequest.from(ReturnOrderModel order) {
    return ReturnOrderEditRequest(
      returnDate: order.returnDate,
      items: order.items
          .map(ReturnOrderItemEditModel.fromItem)
          .toList(growable: false),
    );
  }

  Map<String, dynamic> toJson() => {
    'return_date': returnDate == null ? null : _isoDate(returnDate!),
    'items': items.map((item) => item.toJson()).toList(),
  };

  static String _isoDate(DateTime value) {
    final String month = value.month.toString().padLeft(2, '0');
    final String day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }
}
