import 'package:web/web.dart' as web;

void blockBackNavigation() {
  web.window.history.pushState(null, '', web.window.location.href);
  web.window.onPopState.listen((_) {
    web.window.history.pushState(null, '', web.window.location.href);
  });
}
