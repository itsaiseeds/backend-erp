import '../models/city_model.dart';
import '../models/state_model.dart';
import '../network/api_client.dart';
import '../network/endpoints/utilities_endpoints.dart';

class MetadataService {
  MetadataService._();

  static final MetadataService instance = MetadataService._();

  ApiClient? _apiClient;
  List<StateModel> _states = const [];
  final Map<int, CityModel> _citiesById = {};
  bool _isLoaded = false;
  Future<bool>? _inFlight;

  set apiClient(ApiClient client) => _apiClient = client;

  bool get isLoaded => _isLoaded;

  List<StateModel> get states => List.unmodifiable(_states);

  List<CityModel> get cities => List.unmodifiable(_citiesById.values);

  CityModel? cityById(int? id) => id == null ? null : _citiesById[id];

  StateModel? stateOfCity(int? cityId) {
    if (cityId == null) return null;
    for (final state in _states) {
      for (final city in state.cities) {
        if (city.id == cityId) return state;
      }
    }
    return null;
  }

  Future<bool> loadCities({bool forceRefresh = false}) {
    if (_isLoaded && !forceRefresh) return Future<bool>.value(true);

    final Future<bool>? pending = _inFlight;
    if (pending != null) return pending;

    final Future<bool> request = _fetchCities();
    _inFlight = request;
    return request.whenComplete(() => _inFlight = null);
  }

  Future<bool> _fetchCities() async {
    try {
      final dynamic response = await (_apiClient ??= ApiClient()).get(
        UtilitiesEndpoints.cities,
      );
      if (response is! List) return false;

      final List<StateModel> parsed = response
          .whereType<Map>()
          .map((state) => StateModel.fromJson(Map<String, dynamic>.from(state)))
          .toList();

      _states = parsed;
      _citiesById
        ..clear()
        ..addEntries(
          parsed
              .expand((state) => state.cities)
              .map((city) => MapEntry(city.id, city)),
        );
      _isLoaded = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  void reset() {
    _states = const [];
    _citiesById.clear();
    _isLoaded = false;
    _inFlight = null;
  }
}
