import 'package:flutter/material.dart';
import 'package:mindcore_ai/pages/home_screen.dart';
import 'package:mindcore_ai/pages/chat_screen.dart';
import 'package:mindcore_ai/pages/daily_hub_screen.dart';
import 'package:mindcore_ai/pages/profile_screen.dart' as profile;

Route<T> createSlideRoute<T>(Widget page, {AxisDirection direction = AxisDirection.left}) {
  Offset begin;
  switch (direction) {
    case AxisDirection.right: begin = const Offset(-1.0, 0.0); break;
    case AxisDirection.up:    begin = const Offset(0.0, 1.0);  break;
    case AxisDirection.down:  begin = const Offset(0.0, -1.0); break;
    case AxisDirection.left:
    default:                  begin = const Offset(1.0, 0.0);  break;
  }
  return PageRouteBuilder<T>(
    pageBuilder: (_, __, ___) => page,
    transitionsBuilder: (_, animation, __, child) {
      final tween = Tween(begin: begin, end: Offset.zero).chain(CurveTween(curve: Curves.easeOutCubic));
      return SlideTransition(position: animation.drive(tween), child: child);
    },
  );
}
