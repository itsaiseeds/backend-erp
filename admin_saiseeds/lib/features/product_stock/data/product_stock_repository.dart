import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import '../../bag_stock/data/models/bag_stock_line_model.dart';
import '../../packet_stock/data/models/packet_stock_line_model.dart';
import 'models/product_stock_line_model.dart';

class ProductStockRepository {
  final ApiClient _apiClient;

  const ProductStockRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  // Both halves of the position come from one list call each; get-stock is
  // per-id and would otherwise cost a request per packaging and product.
  Future<List<ProductStockLineModel>> fetchAll() async {
    final List<dynamic> responses = await Future.wait([
      _apiClient.get(InventoryEndpoints.bagStock),
      _apiClient.get(InventoryEndpoints.samplePacketStock),
    ]);

    final dynamic bags = responses.first;
    final dynamic loose = responses.last;

    if (bags is! Map || loose is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    final BagStockSnapshotModel bagSnapshot = BagStockSnapshotModel.fromJson(
      Map<String, dynamic>.from(bags),
    );
    final PacketStockSnapshotModel looseSnapshot =
        PacketStockSnapshotModel.fromJson(Map<String, dynamic>.from(loose));

    return [
      for (final BagStockLineModel line in bagSnapshot.lines)
        ProductStockLineModel(
          publicId: line.packagingPublicId,
          kind: ProductStockKind.bag,
          name: line.productName,
          snapshotDate: bagSnapshot.snapshotDate,
          packetWeight: line.packetWeight,
          onHand: line.onHand,
          reserved: line.reserved,
          consumed: line.consumed,
          available: line.available,
        ),
      for (final PacketStockLineModel line in looseSnapshot.lines)
        ProductStockLineModel(
          publicId: line.productPublicId,
          kind: ProductStockKind.loose,
          name: line.productName,
          snapshotDate: looseSnapshot.snapshotDate,
          packetWeight: line.packetWeight,
          onHand: line.onHand,
          reserved: line.reserved,
          consumed: line.consumed,
          available: line.available,
        ),
    ];
  }
}
