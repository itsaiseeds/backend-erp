import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const double kBarHeight = 48;

Widget _row({required double searchBarIntrinsicHeight}) {
  return MaterialApp(
    home: Scaffold(
      body: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: SizedBox(
                height: searchBarIntrinsicHeight,
                child: const ColoredBox(color: Color(0xFFEEEEEE)),
              ),
            ),
            const SizedBox(width: 12),
            Align(
              alignment: Alignment.topCenter,
              child: SizedBox(
                width: kBarHeight,
                height: kBarHeight,
                child: ColoredBox(
                  color: Color(0xFF2E7D32),
                  child: SizedBox.shrink(key: ValueKey('refresh')),
                ),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('action keeps its height when the search bar is one row',
      (tester) async {
    await tester.pumpWidget(_row(searchBarIntrinsicHeight: kBarHeight));
    expect(tester.getSize(find.byKey(const ValueKey('refresh'))).height,
        kBarHeight);
  });

  testWidgets('action keeps its height when filter chips wrap to two rows',
      (tester) async {
    await tester.pumpWidget(_row(searchBarIntrinsicHeight: 96));

    expect(
      tester.getSize(find.byKey(const ValueKey('refresh'))).height,
      kBarHeight,
      reason: 'refresh must not grow with the search bar',
    );
  });
}
