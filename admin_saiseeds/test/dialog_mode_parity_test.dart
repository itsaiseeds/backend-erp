import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_detail_dialog.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';
import 'package:admin_saiseeds/core/widgets/feedback/detail_field.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/core/widgets/layout/form_field_grid.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const Size _screen = Size(1600, 1000);

Future<void> _pumpView(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = _screen;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AppDetailDialog(
          icon: Icons.groups_outlined,
          title: 'Sales person details',
          subtitle: 'Identity and contact details on record.',
          content: const DetailFieldGrid(
            fields: [
              DetailField(label: 'Name', value: 'Hitesh Mori'),
              DetailField(label: 'Email (optional)', value: 'h@example.com'),
            ],
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _pumpEdit(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = _screen;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AppFormDialog(
          icon: Icons.groups_outlined,
          title: 'Edit Sales Person',
          subtitle: 'Update the sales person account details.',
          submitLabel: 'Update',
          onSubmit: () {},
          content: FormFieldGrid(
            fields: [
              AppTextField(
                controller: TextEditingController(text: 'Hitesh Mori'),
                label: 'Name',
              ),
              AppTextField(
                controller: TextEditingController(text: 'h@example.com'),
                label: 'Email (optional)',
              ),
            ],
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Color _headerColour(WidgetTester tester) {
  final Container header = tester.widget<Container>(
    find
        .descendant(
          of: find.byType(AppDialogHeader),
          matching: find.byType(Container),
        )
        .first,
  );
  return header.color!;
}

Color _cardBorderColour(WidgetTester tester, Type dialog) {
  final Container card = tester.widget<Container>(
    find
        .descendant(of: find.byType(dialog), matching: find.byType(Container))
        .first,
  );
  return ((card.decoration as BoxDecoration).border as Border).top.color;
}

double _fieldGap(WidgetTester tester) =>
    tester.getTopLeft(find.text('h@example.com')).dx -
    tester.getTopLeft(find.text('Hitesh Mori')).dx;

void main() {
  group('view and edit share one look', () {
    testWidgets('both headers are the same accent green', (tester) async {
      await _pumpView(tester);
      final Color view = _headerColour(tester);

      await _pumpEdit(tester);
      final Color edit = _headerColour(tester);

      expect(view, AppColors.PRIMARY);
      expect(edit, view);
    });

    testWidgets('both cards carry the same border', (tester) async {
      await _pumpView(tester);
      final Color view = _cardBorderColour(tester, AppDetailDialog);

      await _pumpEdit(tester);
      final Color edit = _cardBorderColour(tester, AppFormDialog);

      expect(view, AppColors.PRIMARY);
      expect(edit, view);
    });

    testWidgets('both lay fields out in two columns', (tester) async {
      await _pumpView(tester);
      final double view = _fieldGap(tester);

      await _pumpEdit(tester);
      final double edit = _fieldGap(tester);

      // A single-column edit form would stack them, leaving no horizontal gap.
      expect(view, greaterThan(0));
      expect(edit, closeTo(view, 1.0));
    });

    testWidgets('both render values in the same field widget', (tester) async {
      await _pumpView(tester);
      expect(find.byType(AppTextField), findsNWidgets(2));

      await _pumpEdit(tester);
      expect(find.byType(AppTextField), findsNWidgets(2));
    });

    testWidgets('only the enabled state differs', (tester) async {
      await _pumpView(tester);
      for (final TextFormField field in tester.widgetList<TextFormField>(
        find.byType(TextFormField),
      )) {
        expect(field.enabled, isFalse);
      }

      await _pumpEdit(tester);
      for (final TextFormField field in tester.widgetList<TextFormField>(
        find.byType(TextFormField),
      )) {
        expect(field.enabled, isNot(false));
      }
    });

    testWidgets('both use the same dialog width', (tester) async {
      await _pumpView(tester);
      final double view = tester
          .getSize(
            find
                .descendant(
                  of: find.byType(AppDetailDialog),
                  matching: find.byType(ConstrainedBox),
                )
                .first,
          )
          .width;

      await _pumpEdit(tester);
      final double edit = tester
          .getSize(
            find
                .descendant(
                  of: find.byType(AppFormDialog),
                  matching: find.byType(ConstrainedBox),
                )
                .first,
          )
          .width;

      expect(view, AppSizes.detailDialogWidth);
      expect(edit, view);
    });
  });
}
