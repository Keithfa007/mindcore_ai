// lib/widgets/gradient_background.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class GradientBackground extends StatelessWidget {
  final Widget child;
  final bool scrollable;

  const GradientBackground({
    super.key,
    required this.child,
    this.scrollable = false,
  });

  @override
  Widget build(BuildContext context) {
    final content = scrollable
        ? SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: child,
    )
        : child;

    return Container(
      width: double.infinity,
      height: double.infinity,
      decoration: BoxDecoration(
        gradient: AppGradients.body(context),
      ),
      child: SafeArea(child: content),
    );
  }
}
