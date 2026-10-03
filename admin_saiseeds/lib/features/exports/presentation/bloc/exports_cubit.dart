import 'dart:typed_data';

import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/download/file_download.dart';
import '../../data/exports_repository.dart';
import '../../data/models/export_kind.dart';
import '../../../dispatch_challans/data/models/dispatch_challan_model.dart';
import '../../utils/challan_zip_writer.dart';
import '../../utils/excel_writer.dart';
import '../../utils/export_sheets.dart';

enum ExportOutcome { success, empty, failure }

/// What the download should contain.
enum ExportFormat { spreadsheet, receipts }

class ExportResult {
  final ExportOutcome outcome;
  final int rowCount;
  final String? errorMessage;

  const ExportResult({
    required this.outcome,
    this.rowCount = 0,
    this.errorMessage,
  });
}

class ExportsState extends Equatable {
  /// The report currently being built, if any. Only one runs at a time so
  /// the card can show its own progress.
  final ExportKind? busyKind;

  const ExportsState({this.busyKind});

  bool get isBusy => busyKind != null;

  bool isBusyFor(ExportKind kind) => busyKind == kind;

  @override
  List<Object?> get props => [busyKind];
}

class ExportsCubit extends SafeCubit<ExportsState> {
  final ExportsRepository _repository;

  ExportsCubit({required ExportsRepository repository})
    : _repository = repository,
      super(const ExportsState());

  /// Fetches, flattens, encodes and hands the file to the browser.
  ///
  /// An empty report is reported rather than downloaded: a spreadsheet with
  /// only headers looks like a failure to the person who opened it.
  Future<ExportResult> export({
    required ExportKind kind,
    String? startDate,
    String? endDate,
    ExportFormat format = ExportFormat.spreadsheet,
  }) async {
    if (state.isBusy) {
      return const ExportResult(outcome: ExportOutcome.failure);
    }

    emit(ExportsState(busyKind: kind));

    try {
      final Map<String, dynamic> payload = await _repository.fetchExport(
        kind: kind,
        startDate: startDate,
        endDate: endDate,
      );

      if (format == ExportFormat.receipts) {
        return await _downloadReceipts(
          payload: payload,
          kind: kind,
          startDate: startDate,
          endDate: endDate,
        );
      }

      final ExportSheet sheet = ExportSheets.build(kind, payload);
      if (sheet.isEmpty) {
        emit(const ExportsState());
        return const ExportResult(outcome: ExportOutcome.empty);
      }

      final Uint8List bytes = ExcelWriter.build(
        sheetName: kind.label,
        sheet: sheet,
      );

      await downloadBytes(
        bytes: bytes,
        fileName: fileNameFor(kind, startDate: startDate, endDate: endDate),
        mimeType: ExcelWriter.mimeType,
      );

      emit(const ExportsState());
      return ExportResult(
        outcome: ExportOutcome.success,
        rowCount: sheet.rows.length,
      );
    } on ApiException catch (e) {
      emit(const ExportsState());
      return ExportResult(
        outcome: ExportOutcome.failure,
        errorMessage: e.message,
      );
    } catch (_) {
      emit(const ExportsState());
      return const ExportResult(
        outcome: ExportOutcome.failure,
        errorMessage: AppStrings.EXPORT_FAILED,
      );
    }
  }

  /// Bundles one challan PDF per dispatch, using the same generator the
  /// Dispatch Orders tab prints from.
  Future<ExportResult> _downloadReceipts({
    required Map<String, dynamic> payload,
    required ExportKind kind,
    String? startDate,
    String? endDate,
  }) async {
    final dynamic raw = payload['results'];
    final List<DispatchChallanModel> challans = raw is List
        ? raw
              .whereType<Map>()
              .map(
                (item) => DispatchChallanModel.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList()
        : const [];

    if (challans.isEmpty) {
      emit(const ExportsState());
      return const ExportResult(outcome: ExportOutcome.empty);
    }

    final Uint8List bytes = await ChallanZipWriter.build(challans);

    await downloadBytes(
      bytes: bytes,
      fileName: fileNameFor(
        kind,
        startDate: startDate,
        endDate: endDate,
        extension: 'zip',
      ),
      mimeType: ChallanZipWriter.mimeType,
    );

    emit(const ExportsState());
    return ExportResult(
      outcome: ExportOutcome.success,
      rowCount: challans.length,
    );
  }

  /// e.g. `orders_2026-10-01_to_2026-10-03.xlsx`, or just the stem plus the
  /// extension when the report was run without a window.
  static String fileNameFor(
    ExportKind kind, {
    String? startDate,
    String? endDate,
    String extension = 'xlsx',
  }) {
    final String from = startDate?.trim() ?? '';
    final String to = endDate?.trim() ?? '';
    if (from.isEmpty || to.isEmpty) return '${kind.fileStem}.$extension';
    if (from == to) return '${kind.fileStem}_$from.$extension';
    return '${kind.fileStem}_${from}_to_$to.$extension';
  }
}
