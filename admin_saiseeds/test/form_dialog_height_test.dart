import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';

Future<double> _heightWith(WidgetTester tester, int rows) async {
  tester.view.physicalSize = const Size(1400, 1000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: AppFormDialog(
        icon: Icons.inventory_2_outlined,
        title: 'Add Product',
        subtitle: 'sub',
        submitLabel: 'Next',
        onSubmit: () {},
        fixedHeight: AppSizes.formDialogFixedHeight,
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (int i = 0; i < rows; i++)
              const SizedBox(height: 70, child: Text('point')),
          ],
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();

  final Size size = tester.getSize(
    find.byWidgetPredicate(
      (w) => w is Container && w.clipBehavior == Clip.antiAlias,
    ),
  );
  return size.height;
}

void main() {
  testWidgets('footer sits at the bottom of the fixed-height dialog',
      (tester) async {
    tester.view.physicalSize = const Size(1400, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: AppFormDialog(
          icon: Icons.inventory_2_outlined,
          title: 'Add Product',
          subtitle: 'sub',
          submitLabel: 'Next',
          onSubmit: () {},
          fixedHeight: AppSizes.formDialogFixedHeight,
          content: const SizedBox(height: 60, child: Text('short content')),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final Rect card = tester.getRect(
      find.byWidgetPredicate(
        (w) => w is Container && w.clipBehavior == Clip.antiAlias,
      ),
    );
    final Rect button = tester.getRect(find.text('Next'));

    expect(
      card.bottom - button.bottom,
      lessThan(60),
      reason: 'footer must hug the bottom edge, not float mid-dialog',
    );
  });

  testWidgets('dialog height stays fixed as description points are added',
      (tester) async {
    final small = await _heightWith(tester, 1);
    final large = await _heightWith(tester, 12);

    expect(large, small,
        reason: 'adding points must scroll, not grow the dialog');
    expect(small, AppSizes.formDialogFixedHeight);
  });

  testWidgets('content scrolls when it overflows the fixed height',
      (tester) async {
    await _heightWith(tester, 12);

    expect(find.byType(Scrollable), findsWidgets);
  });
}
