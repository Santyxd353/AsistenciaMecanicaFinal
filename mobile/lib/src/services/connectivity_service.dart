import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';

/// Wrapper sobre connectivity_plus.
/// Expone `isOnline$` (bool stream) y `currentOnline` (snapshot).
/// El consumidor (app_controller / offline_queue) escucha y reacciona.
class ConnectivityService {
  ConnectivityService() {
    _connectivity.onConnectivityChanged.listen(_handleChange);
    _bootstrap();
  }

  final _connectivity = Connectivity();
  final _controller = StreamController<bool>.broadcast();
  bool _currentOnline = true;

  Stream<bool> get isOnline$ => _controller.stream;
  bool get currentOnline => _currentOnline;

  Future<void> _bootstrap() async {
    final result = await _connectivity.checkConnectivity();
    _handleChange(result);
  }

  void _handleChange(List<ConnectivityResult> results) {
    final online = results.any((r) => r != ConnectivityResult.none);
    if (online != _currentOnline) {
      _currentOnline = online;
      _controller.add(online);
    }
  }

  void dispose() {
    _controller.close();
  }
}
