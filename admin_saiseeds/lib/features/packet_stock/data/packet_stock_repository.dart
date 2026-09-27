import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import 'models/packet_stock_line_model.dart';

class PacketStockCountEntry {
  final String productPublicId;
  final String packetWeight;
  final int packets;

  const PacketStockCountEntry({
    required this.productPublicId,
    required this.packetWeight,
    required this.packets,
  });

  Map<String, dynamic> toJson() => {
    'product': productPublicId,
    'packet_weight': packetWeight,
    'packets': packets,
  };
}

class PacketStockRepository {
  final ApiClient _apiClient;

  const PacketStockRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PacketStockSnapshotModel> fetchPacketStock() async {
    final dynamic response = await _apiClient.get(
      InventoryEndpoints.samplePacketStock,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PacketStockSnapshotModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<void> replacePacketStock(List<PacketStockCountEntry> counts) async {
    await _apiClient.post(
      InventoryEndpoints.updateSamplePacketStock,
      body: _body(counts),
    );
  }

  Future<void> patchPacketStock(List<PacketStockCountEntry> counts) async {
    await _apiClient.patch(
      InventoryEndpoints.updateSamplePacketStock,
      body: _body(counts),
    );
  }

  static Map<String, dynamic> _body(List<PacketStockCountEntry> counts) => {
    'counts': counts.map((entry) => entry.toJson()).toList(),
  };
}
