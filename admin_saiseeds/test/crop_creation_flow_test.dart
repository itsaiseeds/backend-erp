import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/models/crop_model.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/network/api_exception.dart';
import 'package:admin_saiseeds/core/services/crops_service.dart';
import 'package:admin_saiseeds/core/widgets/inputs/crop_picker_field.dart';
import 'package:admin_saiseeds/features/products/data/crops_repository.dart';

class _CropsStubAdapter implements HttpClientAdapter {
  _CropsStubAdapter({
    required this.listPayload,
    this.createStatusCode = 201,
    this.createPayload,
    this.createErrorDetail,
  });

  final List<Map<String, dynamic>> listPayload;
  final int createStatusCode;
  final Map<String, dynamic>? createPayload;
  final String? createErrorDetail;

  int createCallCount = 0;
  String? lastCreatedName;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.method == 'POST') {
      createCallCount += 1;
      final Map<String, dynamic> body = Map<String, dynamic>.from(
        options.data as Map,
      );
      lastCreatedName = body['name'] as String?;

      if (createErrorDetail != null) {
        return ResponseBody.fromString(
          jsonEncode({'name': createErrorDetail}),
          createStatusCode,
          headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          },
        );
      }

      return ResponseBody.fromString(
        jsonEncode(createPayload),
        createStatusCode,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }

    return ResponseBody.fromString(
      jsonEncode(listPayload),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

CropsRepository _repositoryWith(_CropsStubAdapter adapter) {
  final Dio dio = Dio(
    BaseOptions(
      baseUrl: 'http://stub.local',
      validateStatus: (status) => status != null && status < 500,
    ),
  );
  dio.httpClientAdapter = adapter;
  return CropsRepository(apiClient: ApiClient(dio: dio));
}

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://stub.local');
  });

  setUp(() => CropsService.instance.reset());
  tearDown(() => CropsService.instance.reset());

  group('crop picker options', () {
    const List<CropModel> crops = [
      CropModel(id: 1, name: 'Cotton'),
      CropModel(id: 2, name: 'Wheat'),
    ];

    test('an empty query lists every crop without a create option', () {
      final List<CropPickerOption> options = CropPickerField.optionsFor(
        crops: crops,
        query: '',
      );

      expect(options, hasLength(2));
      expect(options.any((option) => option.isCreate), isFalse);
    });

    test('an unknown name offers a create option first', () {
      final List<CropPickerOption> options = CropPickerField.optionsFor(
        crops: crops,
        query: 'Maize',
      );

      expect(options.first.isCreate, isTrue);
      expect(options.first.createName, 'Maize');
      expect(
        CropPickerField.optionLabel(options.first),
        contains('Maize'),
      );
    });

    test('an exact existing name offers no create option', () {
      final List<CropPickerOption> options = CropPickerField.optionsFor(
        crops: crops,
        query: 'cotton',
      );

      expect(options.any((option) => option.isCreate), isFalse);
    });
  });

  group('crop creation', () {
    test('a created crop joins the cached list and can be selected', () async {
      final _CropsStubAdapter adapter = _CropsStubAdapter(
        listPayload: const [
          {'id': 1, 'name': 'Cotton'},
          {'id': 2, 'name': 'Wheat'},
        ],
        createPayload: const {'id': 3, 'name': 'Maize'},
      );
      CropsService.instance.repository = _repositoryWith(adapter);

      expect(await CropsService.instance.loadCrops(), isTrue);
      expect(CropsService.instance.crops, hasLength(2));

      final CropModel created = await CropsService.instance.createCrop('Maize');

      expect(adapter.createCallCount, 1);
      expect(adapter.lastCreatedName, 'Maize');
      expect(created.id, 3);
      expect(created.name, 'Maize');

      final List<CropModel> cached = CropsService.instance.crops;
      expect(cached, hasLength(3));
      expect(cached.any((crop) => crop.id == 3), isTrue);

      final List<CropPickerOption> options = CropPickerField.optionsFor(
        crops: cached,
        query: 'Maize',
      );
      expect(options.any((option) => option.isCreate), isFalse);
      expect(
        options.any((option) => !option.isCreate && option.crop!.id == 3),
        isTrue,
      );
    });

    test('a duplicate name surfaces the server message and adds nothing', () async {
      final _CropsStubAdapter adapter = _CropsStubAdapter(
        listPayload: const [
          {'id': 1, 'name': 'Cotton'},
        ],
        createStatusCode: 400,
        createErrorDetail: 'A crop with this name already exists.',
      );
      CropsService.instance.repository = _repositoryWith(adapter);

      await CropsService.instance.loadCrops();
      expect(CropsService.instance.crops, hasLength(1));

      await expectLater(
        CropsService.instance.createCrop('Cotton'),
        throwsA(
          isA<ApiException>().having(
            (error) => error.message,
            'message',
            contains('already exists'),
          ),
        ),
      );

      expect(CropsService.instance.crops, hasLength(1));
    });

    test('a failed fetch fails soft with an empty list', () async {
      final Dio dio = Dio(
        BaseOptions(
          baseUrl: 'http://stub.local',
          validateStatus: (status) => status != null && status < 500,
        ),
      );
      dio.httpClientAdapter = _CropsStubAdapter(
        listPayload: const [],
      );
      CropsService.instance.repository = CropsRepository(
        apiClient: ApiClient(dio: dio),
      );

      expect(await CropsService.instance.loadCrops(), isTrue);
      expect(CropsService.instance.crops, isEmpty);
    });
  });
}
