import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'app_gradients.dart';

class AppTopBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;
  final Widget? leading;
  final bool centerTitle;
  final double titleSize;
  final Color? color;

  const AppTopBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.centerTitle = true,
    this.titleSize = 18.5,
    this.color,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 8);

  @override
  Widget build(BuildContext context) {
    final barColor = color ?? const Color(0xCCCDC8F7);
    final brightness = ThemeData.estimateBrightnessForColor(barColor);
    final onBar = (brightness == Brightness.dark) ? Colors.white : Colors.black87;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: (brightness == Brightness.dark)
          ? SystemUiOverlayStyle.light
          : SystemUiOverlayStyle.dark,
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: AppBar(
            toolbarHeight: kToolbarHeight + 4,
            elevation: 0,
            scrolledUnderElevation: 0,
            backgroundColor: barColor,
            surfaceTintColor: Colors.transparent,
            centerTitle: centerTitle,
            leading: leading,
            actions: actions,
            iconTheme: IconThemeData(color: onBar),
            actionsIconTheme: IconThemeData(color: onBar),
            flexibleSpace: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: AppGradients.appBar(context),
                  border: Border(
                    bottom: BorderSide(
                      color: Colors.white.withValues(alpha: 0.28),
                    ),
                  ),
                ),
              ),
            ),
            titleTextStyle: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontSize: titleSize,
                  fontWeight: FontWeight.w800,
                  color: onBar,
                  letterSpacing: -0.3,
                ),
            title: title == 'MindCore AI'
                ? Stack(
                    alignment: Alignment.center,
                    children: [
                      Container(
                        width: 64,
                        height: 24,
                        decoration: BoxDecoration(
                          shape: BoxShape.rectangle,
                          borderRadius: BorderRadius.circular(30),
                          gradient: RadialGradient(
                            colors: [
                              Colors.white.withValues(alpha: 0.24),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                      Text(
                        title,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  )
                : Text(
                    title,
                    overflow: TextOverflow.ellipsis,
                  ),
          ),
        ),
      ),
    );
  }
}
