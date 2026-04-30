import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../repositories.dart';

typedef ForegroundPushHandler =
    void Function({
      required String title,
      required String message,
      int? requestId,
    });

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Firebase puede no estar configurado en builds locales.
  }
}

class PushNotificationsService {
  PushNotificationsService._();

  static bool _initialized = false;
  static ForegroundPushHandler? _foregroundHandler;
  static StreamSubscription<RemoteMessage>? _onMessageSubscription;

  static Future<void> registerDevice({
    required String baseUrl,
    required String accessToken,
    ForegroundPushHandler? onForegroundMessage,
  }) async {
    if (kIsWeb || accessToken.isEmpty) {
      return;
    }

    try {
      if (!_initialized) {
        FirebaseMessaging.onBackgroundMessage(
          firebaseMessagingBackgroundHandler,
        );
        await Firebase.initializeApp();
        _initialized = true;
      }

      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(alert: true, badge: true, sound: true);

      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await ApiClient(
          baseUrl: baseUrl,
          token: accessToken,
        ).registerDeviceToken(token);
      }

      FirebaseMessaging.instance.onTokenRefresh.listen((newToken) async {
        try {
          await ApiClient(
            baseUrl: baseUrl,
            token: accessToken,
          ).registerDeviceToken(newToken);
        } catch (error) {
          debugPrint('No se pudo actualizar token FCM: $error');
        }
      });

      _foregroundHandler = onForegroundMessage;
      _onMessageSubscription ??= FirebaseMessaging.onMessage.listen((message) {
        final notification = message.notification;
        final title = notification?.title ?? 'Asistencia mecanica';
        final body = notification?.body ?? 'Tienes una nueva notificacion.';
        final requestId = int.tryParse(message.data['solicitud_id'] ?? '');
        _foregroundHandler?.call(
          title: title,
          message: body,
          requestId: requestId,
        );
      });
    } catch (error) {
      debugPrint('FCM no configurado o no disponible: $error');
    }
  }
}
