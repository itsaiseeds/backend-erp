import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/buttons/primary_button.dart';
import 'package:admin_saiseeds/core/widgets/buttons/secondary_button.dart';
import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/layout/entry_rail_panel.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/features/clients/data/clients_repository.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_address_model.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_contact_model.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_model.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_status.dart';
import 'package:admin_saiseeds/features/clients/data/models/transport_agency_model.dart';
import 'package:admin_saiseeds/features/clients/presentation/bloc/clients_cubit.dart';
import 'package:admin_saiseeds/features/clients/presentation/widgets/client_record_dialog.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

const ClientModel _client = ClientModel(
  publicId: 'C-0001',
  companyName: 'sgdg',
  companyPhone: '4645451243',
  gstNumber: '24AAAAB0000A1Z5',
  status: ClientStatus.verified,
  isVerified: true,
  createdBy: 'Sales Person User',
  addresses: [
    ClientAddressModel(line1: 'eywy', cityName: 'Rajkot', isPrimary: true),
  ],
  contacts: [
    ClientContactModel(
      name: 'zzvzv',
      phoneNumber: '7989594989',
      role: 'dbsg',
      isPrimary: true,
    ),
  ],
  transportAgencies: [TransportAgencyModel(name: 'dhdhfhdg', isPrimary: true)],
);

ClientsCubit _cubit() => ClientsCubit(
  repository: ClientsRepository(apiClient: ApiClient(dio: Dio())),
);

Future<void> _pump(WidgetTester tester, RecordDialogMode mode) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Scaffold(
          body: ClientRecordDialog(
            cubit: _cubit(),
            client: _client,
            initialMode: mode,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Finder _card() => find
    .descendant(of: find.byType(Dialog), matching: find.byType(Container))
    .first;

void main() {
  testWidgets('view mode shows the first step read-only', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
      expect(field.isMuted, isTrue);
    }
  });

  testWidgets('the step indicator is gone in favour of footer navigation', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    expect(find.text(AppStrings.CLIENT_STEP_ADDRESSES), findsNothing);
    expect(find.text(AppStrings.CLIENT_STEP_CONTACTS), findsNothing);
    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
  });

  testWidgets('view mode can page through every step from the footer', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.SAVE), findsOneWidget);
    expect(find.text(AppStrings.STEP_BACK), findsOneWidget);
  });

  testWidgets('view mode cannot save from the last step', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    for (int i = 0; i < 3; i++) {
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
    }

    final PrimaryButton save = tester.widget<PrimaryButton>(
      find.byType(PrimaryButton),
    );
    expect(save.onPressed, isNull, reason: 'saving belongs to edit mode alone');
  });

  testWidgets('edit mode opens the fields and shows the wizard footer', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    final Map<String, bool> mutedByLabel = {
      for (final AppTextField field in tester.widgetList<AppTextField>(
        find.byType(AppTextField),
      ))
        if (field.label != null) field.label!: field.isMuted,
    };

    expect(mutedByLabel[AppStrings.COLUMN_COMPANY_NAME], isFalse);
    expect(mutedByLabel[AppStrings.COLUMN_COMPANY_PHONE], isFalse);
    expect(mutedByLabel[AppStrings.COLUMN_GST_NUMBER], isFalse);
    expect(mutedByLabel[AppStrings.CLIENT_CREATED_BY_LABEL], isTrue);

    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
  });

  testWidgets('the details fields keep their place across modes', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);
    final Rect company = tester.getRect(
      find.text(AppStrings.COLUMN_COMPANY_NAME),
    );
    final Rect gst = tester.getRect(find.text(AppStrings.COLUMN_GST_NUMBER));

    await _pump(tester, RecordDialogMode.edit);

    expect(tester.getRect(find.text(AppStrings.COLUMN_COMPANY_NAME)), company);
    expect(tester.getRect(find.text(AppStrings.COLUMN_GST_NUMBER)), gst);
  });

  testWidgets('view mode offers no add-entry action on a list step', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.CLIENT_ADD_ADDRESS), findsNothing);
  });

  testWidgets('edit mode offers the add-entry action on a list step', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.CLIENT_ADD_ADDRESS), findsOneWidget);
  });

  testWidgets('the footer cancel becomes back once past the first step', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);
    expect(find.text(AppStrings.CANCEL), findsOneWidget);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.STEP_BACK), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsNothing);
  });

  testWidgets('back returns to the previous step', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.CLIENT_ADD_ADDRESS), findsNothing);

    await tester.tap(find.text(AppStrings.STEP_BACK));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.COLUMN_COMPANY_NAME), findsOneWidget);
  });

  testWidgets('the footer buttons share one width', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final double back = tester
        .getSize(
          find.ancestor(
            of: find.text(AppStrings.STEP_BACK),
            matching: find.byType(SecondaryButton),
          ),
        )
        .width;
    final double next = tester
        .getSize(
          find.ancestor(
            of: find.text(AppStrings.STEP_NEXT),
            matching: find.byType(PrimaryButton),
          ),
        )
        .width;

    expect(next, back);
  });

  testWidgets('the entry rail flags the primary entry in brand green', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final Iterable<Text> primaries = tester.widgetList<Text>(
      find.text(AppStrings.CLIENT_PRIMARY_BADGE),
    );
    expect(
      primaries.any((text) => text.style?.color == AppColors.SUCCESS),
      isTrue,
    );
  });

  testWidgets('the entry rail lists every entry and selects the first', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.byType(EntryRailPanel), findsOneWidget);
    expect(find.text(AppStrings.CLIENT_RAIL_ADDRESSES_HINT), findsOneWidget);

    final EntryRailPanel rail = tester.widget<EntryRailPanel>(
      find.byType(EntryRailPanel),
    );
    expect(rail.entries.length, 1);
    expect(rail.selectedIndex, 0);
  });

  testWidgets('every step keeps one dialog height', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    final double detailsHeight = tester.getSize(_card()).height;
    final List<double> stepHeights = [];

    for (int i = 0; i < 3; i++) {
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
      stepHeights.add(tester.getSize(_card()).height);
    }

    for (final double height in stepHeights) {
      expect(height, detailsHeight);
    }
  });

  testWidgets('the footer rests on the card floor on every step', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    for (int step = 0; step < 4; step++) {
      final double cardBottom = tester.getRect(_card()).bottom;
      final String label = step == 3 ? AppStrings.SAVE : AppStrings.STEP_NEXT;
      final double buttonBottom = tester.getRect(find.text(label)).bottom;

      expect(
        cardBottom - buttonBottom,
        lessThan(AppSpacing.xxl),
        reason: 'footer drifted up on step ${step + 1}',
      );

      if (step == 3) break;
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('the rail runs flush to the dialog edge', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final Rect card = tester.getRect(_card());
    final Rect rail = tester.getRect(find.byType(EntryRailPanel));

    // The only gap is the card's own hairline border.
    expect(rail.left - card.left, lessThanOrEqualTo(AppSizes.borderThin));
    expect(card.right - rail.right, lessThanOrEqualTo(AppSizes.borderThin));
  });

  testWidgets('the rail offers no add or remove in view mode', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final EntryRailPanel rail = tester.widget<EntryRailPanel>(
      find.byType(EntryRailPanel),
    );
    expect(rail.onAdd, isNull);
    expect(rail.onRemove, isNull);
  });

  testWidgets('the rail offers add in edit mode', (tester) async {
    await _pump(tester, RecordDialogMode.edit);
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final EntryRailPanel rail = tester.widget<EntryRailPanel>(
      find.byType(EntryRailPanel),
    );
    expect(rail.onAdd, isNotNull);
  });

  testWidgets('adding an entry selects it in the rail', (tester) async {
    await _pump(tester, RecordDialogMode.edit);
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.CLIENT_ADD_ADDRESS));
    await tester.pumpAndSettle();

    final EntryRailPanel rail = tester.widget<EntryRailPanel>(
      find.byType(EntryRailPanel),
    );
    expect(rail.entries.length, 2);
    expect(rail.selectedIndex, 1);
  });

  testWidgets('the status badge renders in both modes', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    expect(find.text(AppStrings.CLIENT_STATUS_VERIFIED), findsOneWidget);

    await _pump(tester, RecordDialogMode.edit);
    expect(find.text(AppStrings.CLIENT_STATUS_VERIFIED), findsOneWidget);
  });

  testWidgets('the status badge lives in the header, not the body', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    final Rect badge = tester.getRect(
      find.text(AppStrings.CLIENT_STATUS_VERIFIED),
    );
    final Rect title = tester.getRect(
      find.text(AppStrings.CLIENT_DETAILS_TITLE),
    );
    final Rect company = tester.getRect(
      find.text(AppStrings.COLUMN_COMPANY_NAME),
    );

    expect(badge.center.dy, lessThan(company.top));
    expect(badge.center.dy, closeTo(title.center.dy, title.height * 2));
  });

  testWidgets('the badge stays in the header on a list step', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final Rect badge = tester.getRect(
      find.text(AppStrings.CLIENT_STATUS_VERIFIED),
    );
    final Rect rail = tester.getRect(find.byType(EntryRailPanel));

    expect(badge.bottom, lessThanOrEqualTo(rail.top));
  });
}
