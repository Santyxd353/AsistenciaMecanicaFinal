import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

/// Cliente WebSocket para los rooms de realtime del backend:
///   /api/v1/ws/solicitudes/{id}?token=...
///   /api/v1/ws/talleres/{id}?token=...
///   /api/v1/ws/tecnicos/{id}?token=...
///   /api/v1/ws/chat/{id}?token=...
///
/// Eventos esperados (JSON con `event` y `payload`):
///   solicitud.actualizada, tracking.update, cotizacion.nueva,
///   cotizacion.aceptada, chat.mensaje.
///
/// Reconexión exponencial 1s -> 2s -> 4s ... cap 30s. Cierra al `dispose`.
class RealtimeService {
  RealtimeService({required this.baseUrl, required this.token});

  final String baseUrl; // ej "https://backend.run.app" o "http://10.0.2.2:8000"
  final String token;

  final Map<String, _Room> _rooms = {};

  /// Suscribirse a una sala. Devuelve un Stream de eventos parseados.
  /// Mientras haya al menos un listener el socket se mantiene abierto.
  Stream<RealtimeEvent> subscribe(String kind, int id) {
    final key = '$kind:$id';
    var room = _rooms[key];
    if (room == null) {
      room = _Room(_buildUri(kind, id));
      _rooms[key] = room;
      room.connect();
    }
    return room.controller.stream;
  }

  Uri _buildUri(String kind, int id) {
    final mapped = const {
      'solicitud': 'solicitudes',
      'taller': 'talleres',
      'tecnico': 'tecnicos',
      'chat': 'chat',
    }[kind];
    if (mapped == null) {
      throw ArgumentError('kind invalido: $kind');
    }
    final base = baseUrl
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
    return Uri.parse('$base/api/v1/ws/$mapped/$id?token=$token');
  }

  void unsubscribe(String kind, int id) {
    final key = '$kind:$id';
    _rooms.remove(key)?.dispose();
  }

  void dispose() {
    for (final r in _rooms.values) {
      r.dispose();
    }
    _rooms.clear();
  }
}

class _Room {
  _Room(this.uri);
  final Uri uri;
  final controller = StreamController<RealtimeEvent>.broadcast();
  WebSocketChannel? _channel;
  int _retries = 0;
  bool _closed = false;
  Timer? _retryTimer;

  void connect() {
    if (_closed) return;
    try {
      _channel = WebSocketChannel.connect(uri);
      _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _scheduleReconnect,
        cancelOnError: true,
      );
      _retries = 0;
    } catch (e) {
      _onError(e);
    }
  }

  void _onMessage(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      controller.add(
        RealtimeEvent(
          event: data['event']?.toString() ?? 'unknown',
          payload: data['payload'] ?? data,
        ),
      );
    } catch (_) {
      // ignora mensajes no-JSON (p.ej. pings)
    }
  }

  void _onError(Object _) => _scheduleReconnect();

  void _scheduleReconnect() {
    if (_closed) return;
    final delaySec = (1 << _retries.clamp(0, 5)).clamp(1, 30);
    _retries++;
    _retryTimer = Timer(Duration(seconds: delaySec), connect);
  }

  void dispose() {
    _closed = true;
    _retryTimer?.cancel();
    _channel?.sink.close();
    controller.close();
  }
}

class RealtimeEvent {
  RealtimeEvent({required this.event, required this.payload});
  final String event;
  final dynamic payload;
}
