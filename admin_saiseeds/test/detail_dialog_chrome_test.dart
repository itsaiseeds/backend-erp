import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_detail_dialog.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';
import 'package:admin_saiseeds/core/widgets/feedback/detail_field.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<int> _pumpDetail(
  WidgetTester tester, {
  bool withEdit = true,
  Size screen = const Size(1600, 1000),
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = screen;
  addTearDown(tester.view.reset);

  int editTaps = 0;

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () => showDialog<void>(
              context: context,
              builder: (_) => AppDetailDialog(
                icon: Icons.inventory_2_outlined,
                title: 'Product details',
                subtitle: 'Step 1: Basics',
                headerAction: withEdit
                    ? DialogHeaderAction(
                        icon: Icons.edit_outlined,
                        tooltip: AppStrings.EDIT,
                        onPressed: () => editTaps++,
                      )
                    : null,
                content: const DetailFieldGrid(
                  fields: [
                    DetailField(label: 'Name', value: 'SAI-33'),
                    DetailField(label: 'Crop', value: 'Castor'),
                  ],
                ),
              ),
            ),
            child: const Text('open'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
  return editTaps;
}

Size _cardSize(WidgetTester tester) => tester.getSize(
  find
      .descendant(
        of: find.byType(AppDetailDialog),
        matching: find.byType(ConstrainedBox),
      )
      .first,
);

BoxDecoration _cardDecoration(WidgetTester tester) {
  final Container card = tester.widget<Container>(
    find
        .descendant(
          of: find.byType(AppDetailDialog),
          matching: find.byType(Container),
        )
        .first,
  );
  return card.decoration as BoxDecoration;
}

void main() {
  group('dialog chrome', () {
    testWidgets('the card border matches the accent, not a grey line', (
      tester,
    ) async {
      await _pumpDetail(tester);

      final BoxDecoration decoration = _cardDecoration(tester);
      final BorderSide side = (decoration.border as Border).top;

      // A grey border above a green header reads as a stray white edge.
      expect(side.color, AppColors.PRIMARY);
      expect(side.color, isNot(AppColors.BORDER));
    });

    testWidgets('the dialog is wide enough for two columns', (tester) async {
      await _pumpDetail(tester);

      expect(_cardSize(tester).width, AppSizes.detailDialogWidth);
      expect(_cardSize(tester).width, greaterThanOrEqualTo(900));
    });

    testWidgets('a narrow window shrinks the dialog instead of clipping', (
      tester,
    ) async {
      const Size screen = Size(700, 900);
      await _pumpDetail(tester, screen: screen);

      expect(
        _cardSize(tester).width,
        closeTo(screen.width - AppSpacing.lg * 2, 1.0),
      );
    });
  });

  group('view mode fields', () {
    testWidgets('values render in the same field the edit form uses', (
      tester,
    ) async {
      await _pumpDetail(tester);

      // View and edit must not be two different components for one record.
      expect(find.byType(AppTextField), findsNWidgets(2));

      final Iterable<TextFormField> fields = tester.widgetList<TextFormField>(
        find.byType(TextFormField),
      );
      for (final TextFormField field in fields) {
        expect(field.enabled, isFalse);
      }
    });

    testWidgets('two fields sit side by side on a wide dialog', (tester) async {
      await _pumpDetail(tester);

      final double nameX = tester.getTopLeft(find.text('SAI-33')).dx;
      final double cropX = tester.getTopLeft(find.text('Castor')).dx;

      expect(cropX, greaterThan(nameX));
      expect(
        tester.getTopLeft(find.text('SAI-33')).dy,
        closeTo(tester.getTopLeft(find.text('Castor')).dy, 1.0),
      );
    });
  });

  group('the header edit action', () {
    testWidgets('appears when an edit handler is given', (tester) async {
      await _pumpDetail(tester);

      expect(find.byType(DialogHeaderAction), findsOneWidget);
      expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    });

    testWidgets('is absent for a read-only record', (tester) async {
      await _pumpDetail(tester, withEdit: false);

      expect(find.byType(DialogHeaderAction), findsNothing);
      expect(find.byIcon(Icons.edit_outlined), findsNothing);
    });

    testWidgets('the edit icon is white on the accent header', (tester) async {
      await _pumpDetail(tester);

      final Icon icon = tester.widget<Icon>(
        find.descendant(
          of: find.byType(DialogHeaderAction),
          matching: find.byIcon(Icons.edit_outlined),
        ),
      );
      expect(icon.color, AppColors.WHITE);
    });
  });
}
