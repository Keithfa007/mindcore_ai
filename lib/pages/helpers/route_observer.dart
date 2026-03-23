import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

final RouteObserver<ModalRoute<dynamic>> appRouteObserver =
    RouteObserver<ModalRoute<dynamic>>();

mixin AutoStopTtsRouteAware<T extends StatefulWidget> on State<T>
    implements RouteAware {
  bool _routeAwareSubscribed = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_routeAwareSubscribed) return;
    final route = ModalRoute.of(context);
    if (route is PageRoute) {
      appRouteObserver.subscribe(this, route);
      _routeAwareSubscribed = true;
    }
  }

  @override
  void dispose() {
    if (_routeAwareSubscribed) {
      appRouteObserver.unsubscribe(this);
    }
    super.dispose();
  }

  @override
  void didPush() {}

  @override
  void didPopNext() {}

  @override
  void didPushNext() {
    OpenAiTtsService.instance.stop();
  }

  @override
  void didPop() {
    OpenAiTtsService.instance.stop();
  }
}
