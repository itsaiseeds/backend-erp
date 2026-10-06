import '../network/api_client.dart';
import '../../features/parties/data/models/paginated_parties_model.dart';
import '../../features/parties/data/models/party_model.dart';
import '../../features/parties/data/parties_repository.dart';

class PartiesService {
  PartiesService._();

  static final PartiesService instance = PartiesService._();

  PartiesRepository? _repository;
  final List<PartyModel> _parties = [];
  bool _isLoaded = false;

  set repository(PartiesRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<PartyModel> get parties => List.unmodifiable(_parties);

  /// Parties the raw-material inward form may pick from.
  List<PartyModel> get rawMaterialParties =>
      List.unmodifiable(_parties.where((party) => party.isRawMaterial));

  /// Parties the other-material inward form may pick from.
  List<PartyModel> get otherMaterialParties =>
      List.unmodifiable(_parties.where((party) => party.isOtherMaterial));

  PartiesRepository get _resolvedRepository =>
      _repository ??= PartiesRepository(apiClient: ApiClient());

  PartyModel? partyById(int? id) {
    if (id == null) return null;
    for (final PartyModel party in _parties) {
      if (party.id == id) return party;
    }
    return null;
  }

  Future<bool> loadParties({bool forceRefresh = false}) async {
    if (_isLoaded && !forceRefresh) return true;

    try {
      // One call with all=true instead of walking pages: the endpoint
      // returns every row, so nothing is missed and nothing is capped.
      final PaginatedPartiesModel result = await _resolvedRepository
          .fetchParties(queryParams: const {'all': true});
      final List<PartyModel> collected = result.results;

      _parties
        ..clear()
        ..addAll(collected);
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _parties.clear();
    _isLoaded = false;
    _repository = null;
  }
}
