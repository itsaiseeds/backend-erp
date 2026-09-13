import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/widgets/feedback/image_viewer_dialog.dart';

void main() {
  testWidgets('zoom in and out adjust the reported scale', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ImageViewerDialog(url: 'https://example.com/x.jpg', title: 'P'),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('100%'), findsOneWidget);

    await tester.tap(find.byTooltip('Zoom in'));
    await tester.pump();
    expect(find.text('150%'), findsOneWidget);

    await tester.tap(find.byTooltip('Zoom in'));
    await tester.pump();
    expect(find.text('200%'), findsOneWidget);

    await tester.tap(find.byTooltip('Zoom out'));
    await tester.pump();
    expect(find.text('150%'), findsOneWidget);

    await tester.tap(find.byTooltip('Reset zoom'));
    await tester.pump();
    expect(find.text('100%'), findsOneWidget);
  });

  testWidgets('zoom out is disabled at minimum scale', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ImageViewerDialog(url: 'https://example.com/x.jpg'),
        ),
      ),
    );
    await tester.pump();

    // Tapping a disabled control must not change the scale.
    await tester.tap(find.byTooltip('Zoom out'));
    await tester.pump();

    expect(find.text('100%'), findsOneWidget);
  });

  testWidgets('the image is pan/zoom capable', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ImageViewerDialog(url: 'https://example.com/x.jpg'),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(InteractiveViewer), findsOneWidget);
  });
}
