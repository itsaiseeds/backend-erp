import '../network/api_client.dart';
import '../../features/parties/data/models/paginated_parties_model.dart';
import '../../features/parties/data/models/party_model.dart';
import '../../features/parties/data/parties_repository.dart';

class PartiesService {
  PartiesService._();

  static final PartiesService instance = PartiesService._();

  static const int _PAGE_SIZE = 30;
  static const int _MAX_PAGES = 40;

  PartiesRepository? _repository;
  final List<PartyModel> _parties = [];
  bool _isLoaded = false;

  set repository(PartiesRepository value) => _repository = value;

  bool get isLoaded => _isLoaded;

  List<PartyModel> get parties => List.unmodifiable(_parties);

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
      final List<PartyModel> collected = [];

      for (int page = 1; page <= _MAX_PAGES; page++) {
        final PaginatedPartiesModel result = await _resolvedRepository
            .fetchParties(
              queryParams: {'page': page, 'page_size': _PAGE_SIZE},
            );

        collected.addAll(result.results);

        final int? next = result.nextPageNumber;
        if (next == null || next <= page || result.results.isEmpty) break;
      }

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
