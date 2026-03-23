import 'package:flutter/material.dart';
import 'gradient_background.dart';
import 'app_bottom_nav.dart';
import 'app_top_bar.dart';

class PageScaffold extends StatelessWidget {
  final String? title; // if given, uses AppTopBar
  final PreferredSizeWidget? appBar; // OR pass your own AppBar
  final Widget body;
  final int? bottomIndex; // show AppBottomNav when provided
  final Widget? floatingActionButton;
  final bool extendBodyBehindAppBar;

  const PageScaffold({
    super.key,
    required this.body,
    this.title,
    this.appBar,
    this.bottomIndex,
    this.floatingActionButton,
    this.extendBodyBehindAppBar = false,
  });

  @override
  Widget build(BuildContext context) {
    // If appBar is provided, use it.
    // Otherwise, if title is provided, build an AppTopBar.
    // Only on Home, we show the MindReset logo as an action.
    final bar = appBar ??
        (title != null
            ? AppTopBar(
          title: title!,
          actions: title == 'MindReset AI'
              ? <Widget>[
            //Padding(
              //padding: const EdgeInsets.only(right: 12),
              //child: Image.asset(
                //'assets/images/logo512.png', // adjust if your logo path is different
                //height: 50,
              //),
            //),
          ]
              : null,
        )
            : null);

    return Scaffold(
      extendBody: true,
      extendBodyBehindAppBar: extendBodyBehindAppBar,
      appBar: bar,
      body: GradientBackground(
        child: SafeArea(
          top: bar == null, // SafeArea only if no app bar
          child: body,
        ),
      ),
      bottomNavigationBar: bottomIndex != null
          ? AppBottomNav(currentIndex: bottomIndex!)
          : null,
      floatingActionButton: floatingActionButton,
    );
  }
}
