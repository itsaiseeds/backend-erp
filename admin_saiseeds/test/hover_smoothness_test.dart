import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/widgets/buttons/outlined_action_button.dart';

void main() {
  testWidgets('outlined button fades its hover tint instead of snapping',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: OutlinedActionButton(
              label: 'Accept',
              icon: Icons.check,
              onPressed: () {},
            ),
          ),
        ),
      ),
    );

    Color? fill() {
      final c = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );
      return (c.decoration as BoxDecoration?)?.color;
    }

    expect(fill()?.a, 0, reason: 'starts transparent');

    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);
    await gesture.moveTo(tester.getCenter(find.byType(OutlinedActionButton)));
    await tester.pump();

    // Mid-flight: the AnimatedContainer target is set but the painted
    // value is still interpolating.
    await tester.pump(const Duration(milliseconds: 80));
    await tester.pumpAndSettle();

    expect(fill()?.a, greaterThan(0), reason: 'hover tint applied');
  });
}
