import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/models/crop_model.dart';
import 'package:admin_saiseeds/core/models/stage_model.dart';
import 'package:admin_saiseeds/core/widgets/buttons/primary_button.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/core/widgets/inputs/searchable_field.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';
import 'package:admin_saiseeds/features/products/presentation/widgets/product_record_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

const ProductModel _product = ProductModel(
  publicId: 'P-0001',
  name: 'SAI-33',
  crop: CropModel(id: 1, name: 'Castor'),
  stage: StageModel(id: 1, code: 'BREEDER', name: 'Breeder'),
  sellingPrice: '120',
  descriptionItems: ['High yield'],
);

Future<void> _pump(WidgetTester tester, RecordDialogMode mode) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Scaffold(
          body: ProductRecordDialog(product: _product, initialMode: mode),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Finder _card() =>
    find.descendant(of: find.byType(Dialog), matching: find.byType(Container)).first;

void main() {
  testWidgets('view and edit share one title', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    expect(find.text(AppStrings.PRODUCT_DETAIL_TITLE), findsOneWidget);

    await _pump(tester, RecordDialogMode.edit);
    expect(find.text(AppStrings.PRODUCT_DETAIL_TITLE), findsOneWidget);
  });

  testWidgets('view mode is read-only and offers the edit affordance', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
      expect(field.isMuted, isTrue);
    }
    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
  });

  testWidgets('edit mode opens the basics fields', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    final Map<String, bool> mutedByLabel = {
      for (final AppTextField field in tester.widgetList<AppTextField>(
        find.byType(AppTextField),
      ))
        if (field.label != null && field.label!.isNotEmpty)
          field.label!: field.isMuted,
    };

    expect(mutedByLabel[AppStrings.FIELD_PRODUCT_NAME], isFalse);
    expect(mutedByLabel[AppStrings.FIELD_SELLING_PRICE], isFalse);
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
  });

  testWidgets('the basics fields keep their place across modes', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);
    final Rect name = tester.getRect(
      find.text(AppStrings.FIELD_PRODUCT_NAME),
    );
    final Rect price = tester.getRect(
      find.text(AppStrings.FIELD_SELLING_PRICE),
    );

    await _pump(tester, RecordDialogMode.edit);

    expect(tester.getRect(find.text(AppStrings.FIELD_PRODUCT_NAME)), name);
    expect(tester.getRect(find.text(AppStrings.FIELD_SELLING_PRICE)), price);
  });

  testWidgets('every step keeps one dialog height', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    final double first = tester.getSize(_card()).height;

    for (int i = 0; i < 2; i++) {
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
      expect(tester.getSize(_card()).height, first);
    }
  });

  testWidgets('view mode pages through every step from the footer', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.PRODUCT_DESCRIPTION_LABEL), findsOneWidget);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.UPDATE), findsOneWidget);
    expect(find.text(AppStrings.STEP_BACK), findsOneWidget);
  });

  testWidgets('view mode cannot submit from the last step', (tester) async {
    await _pump(tester, RecordDialogMode.view);

    for (int i = 0; i < 2; i++) {
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
    }

    final PrimaryButton submit = tester.widget<PrimaryButton>(
      find.byType(PrimaryButton),
    );
    expect(submit.onPressed, isNull);
  });

  testWidgets('stage sits on the basics step beside selling price', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    final Rect stage = tester.getRect(
      find.byType(SearchableField<StageModel>),
    );
    final Rect price = tester.getRect(
      find.text(AppStrings.FIELD_SELLING_PRICE),
    );

    expect(stage.center.dy, closeTo(price.center.dy, price.height * 4));
    expect(stage.left, greaterThan(price.right));
  });

  testWidgets('the details step carries description points alone', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.PRODUCT_DESCRIPTION_LABEL), findsOneWidget);
    expect(find.byType(SearchableField<StageModel>), findsNothing);
  });

  testWidgets('a description row centres its delete button on the field', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    final Rect field = tester.getRect(find.byType(TextFormField).first);
    final Rect remove = tester.getRect(
      find.byTooltip(AppStrings.PRODUCT_REMOVE_POINT),
    );

    expect(remove.center.dy, closeTo(field.center.dy, 1.0));
  });

  testWidgets('the description editor is edit-only', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.PRODUCT_ADD_POINT), findsNothing);
  });

  testWidgets('the description editor appears in edit mode', (tester) async {
    await _pump(tester, RecordDialogMode.edit);
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.PRODUCT_ADD_POINT), findsOneWidget);
  });

  testWidgets('the image picker is edit-only', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    for (int i = 0; i < 2; i++) {
      await tester.tap(find.text(AppStrings.STEP_NEXT));
      await tester.pumpAndSettle();
    }

    expect(find.text(AppStrings.PRODUCT_PICK_IMAGE), findsNothing);
    expect(find.text(AppStrings.PRODUCT_REPLACE_IMAGE), findsNothing);
  });

  testWidgets('cancelling returns to a read-only view', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.CANCEL));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
    }
  });
}
