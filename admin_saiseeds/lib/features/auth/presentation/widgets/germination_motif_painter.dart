import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';

class GerminationMotifPainter extends CustomPainter {
  final Color strokeColor;
  final double opacityScale;

  const GerminationMotifPainter({
    this.strokeColor = AppColors.WHITE,
    this.opacityScale = 1.0,
  });

  static const int _radiantCount = 9;
  static const int _fieldLineCount = 7;
  static const double _seedRadiusRatio = 0.085;
  static const double _hairlineWidth = 1.0;
  static const double _strokeWidth = 1.4;

  static const double _radiantOpacity = 0.10;
  static const double _fieldOpacity = 0.055;
  static const double _horizonOpacity = 0.16;
  static const double _seedOpacity = 0.20;
  static const double _sproutOpacity = 0.26;

  Color _stroke(double opacity) =>
      strokeColor.withValues(alpha: (opacity * opacityScale).clamp(0.0, 1.0));

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;

    final Offset origin = Offset(size.width * 0.72, size.height * 0.68);
    final double seedRadius =
        math.min(size.width, size.height) * _seedRadiusRatio;

    _paintFieldLattice(canvas, size);
    _paintRadiants(canvas, size, origin, seedRadius);
    _paintHorizon(canvas, size, origin, seedRadius);
    _paintSeed(canvas, origin, seedRadius);
    _paintSprout(canvas, origin, seedRadius);
  }

  void _paintFieldLattice(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _hairlineWidth
      ..color = _stroke(_fieldOpacity);

    final double span = size.width + size.height;
    final double step = span / (_fieldLineCount + 1);

    for (int index = 1; index <= _fieldLineCount; index++) {
      final double offset = step * index;
      canvas.drawLine(
        Offset(offset - size.height, 0),
        Offset(offset, size.height),
        paint,
      );
    }
  }

  void _paintRadiants(
    Canvas canvas,
    Size size,
    Offset origin,
    double seedRadius,
  ) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _hairlineWidth
      ..strokeCap = StrokeCap.round
      ..color = _stroke(_radiantOpacity);

    final double reach = math.max(size.width, size.height);
    const double sweepStart = math.pi;
    const double sweepEnd = math.pi * 2;
    final double stepAngle = (sweepEnd - sweepStart) / (_radiantCount - 1);

    for (int index = 0; index < _radiantCount; index++) {
      final double angle = sweepStart + stepAngle * index;
      final Offset start = Offset(
        origin.dx + math.cos(angle) * (seedRadius * 1.9),
        origin.dy + math.sin(angle) * (seedRadius * 1.9),
      );
      final Offset end = Offset(
        origin.dx + math.cos(angle) * reach,
        origin.dy + math.sin(angle) * reach,
      );
      canvas.drawLine(start, end, paint);
    }

    for (int ring = 1; ring <= 3; ring++) {
      final double ringRadius = seedRadius * (2.6 + ring * 1.9);
      canvas.drawArc(
        Rect.fromCircle(center: origin, radius: ringRadius),
        sweepStart,
        sweepEnd - sweepStart,
        false,
        paint,
      );
    }
  }

  void _paintHorizon(
    Canvas canvas,
    Size size,
    Offset origin,
    double seedRadius,
  ) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _strokeWidth
      ..color = _stroke(_horizonOpacity);

    canvas.drawLine(
      Offset(0, origin.dy),
      Offset(origin.dx - seedRadius * 1.6, origin.dy),
      paint,
    );
    canvas.drawLine(
      Offset(origin.dx + seedRadius * 1.6, origin.dy),
      Offset(size.width, origin.dy),
      paint,
    );
  }

  void _paintSeed(Canvas canvas, Offset origin, double seedRadius) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _strokeWidth
      ..color = _stroke(_seedOpacity);

    final Path seed = Path()
      ..moveTo(origin.dx, origin.dy - seedRadius * 1.35)
      ..cubicTo(
        origin.dx + seedRadius * 1.15,
        origin.dy - seedRadius * 0.75,
        origin.dx + seedRadius * 0.95,
        origin.dy + seedRadius * 0.95,
        origin.dx,
        origin.dy + seedRadius * 1.35,
      )
      ..cubicTo(
        origin.dx - seedRadius * 0.95,
        origin.dy + seedRadius * 0.95,
        origin.dx - seedRadius * 1.15,
        origin.dy - seedRadius * 0.75,
        origin.dx,
        origin.dy - seedRadius * 1.35,
      );

    canvas.drawPath(seed, paint);

    canvas.drawLine(
      Offset(origin.dx, origin.dy - seedRadius * 0.85),
      Offset(origin.dx, origin.dy + seedRadius * 0.85),
      paint,
    );
  }

  void _paintSprout(Canvas canvas, Offset origin, double seedRadius) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = _strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = _stroke(_sproutOpacity);

    final double stemHeight = seedRadius * 3.4;
    final Offset stemTop = Offset(
      origin.dx,
      origin.dy - seedRadius * 1.35 - stemHeight,
    );

    final Path stem = Path()
      ..moveTo(origin.dx, origin.dy - seedRadius * 1.35)
      ..quadraticBezierTo(
        origin.dx - seedRadius * 0.35,
        origin.dy - seedRadius * 1.35 - stemHeight * 0.55,
        stemTop.dx,
        stemTop.dy,
      );
    canvas.drawPath(stem, paint);

    _paintLeaf(canvas, paint, stemTop, seedRadius, isLeft: true);
    _paintLeaf(canvas, paint, stemTop, seedRadius, isLeft: false);
  }

  void _paintLeaf(
    Canvas canvas,
    Paint paint,
    Offset stemTop,
    double seedRadius, {
    required bool isLeft,
  }) {
    final double direction = isLeft ? -1.0 : 1.0;
    final double leafLength = seedRadius * 2.2;
    final double leafDepth = seedRadius * 0.95;
    final Offset anchor = Offset(
      stemTop.dx,
      stemTop.dy + (isLeft ? seedRadius * 0.15 : seedRadius * 0.55),
    );
    final Offset tip = Offset(
      anchor.dx + direction * leafLength,
      anchor.dy - leafDepth * 0.85,
    );

    final Path leaf = Path()
      ..moveTo(anchor.dx, anchor.dy)
      ..quadraticBezierTo(
        anchor.dx + direction * leafLength * 0.45,
        anchor.dy - leafDepth * 1.25,
        tip.dx,
        tip.dy,
      )
      ..quadraticBezierTo(
        anchor.dx + direction * leafLength * 0.55,
        anchor.dy + leafDepth * 0.25,
        anchor.dx,
        anchor.dy,
      );

    canvas.drawPath(leaf, paint);
  }

  @override
  bool shouldRepaint(covariant GerminationMotifPainter oldDelegate) =>
      oldDelegate.strokeColor != strokeColor ||
      oldDelegate.opacityScale != opacityScale;
}
