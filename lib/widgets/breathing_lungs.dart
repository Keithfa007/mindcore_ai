// lib/widgets/breathing_lungs.dart
import 'package:flutter/material.dart';

class BreathingLungs extends StatelessWidget {
  final double scaleX;
  final double scaleY;

  const BreathingLungs({
    super.key,
    required this.scaleX,
    required this.scaleY,
  });

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: Center(
        child: Transform(
          alignment: Alignment.center,
          transform: Matrix4.diagonal3Values(scaleX, scaleY, 1.0),
          child: Image.asset(
            'assets/images/healthy_lungs.png', // make sure this matches your asset
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }
}
