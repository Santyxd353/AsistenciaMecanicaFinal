import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:onesignal_flutter/onesignal_flutter.dart';

import '../app_config.dart';
import '../models.dart';
import '../repositories.dart';

typedef ForegroundPushHandler =
    void Function({
      required String title,
      required String message,
      int? requestId,
    });

typedef PushTapHandler = void Function(int requestId);

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
  static bool _oneSignalClickListenerReady = false;
  static ForegroundPushHandler? _foregroundHandler;
  static PushTapHandler? _tapHandler;
  static StreamSubscription<RemoteMessage>? _onMessageSubscription;
  static StreamSubscription<RemoteMessage>? _onMessageOpenedSubscription;

  static Future<void> registerDevice({
    required String baseUrl,
    required String accessToken,
    required AppUser currentUser,
    ForegroundPushHandler? onForegroundMessage,
    PushTapHandler? onTapRequest,
  }) async {
    if (kIsWeb || accessToken.isEmpty) {
      return;
    }

    _tapHandler = onTapRequest;

    if (AppConfig.oneSignalAppId.isNotEmpty) {
      try {
        final externalId = _buildExternalId(currentUser);
        await OneSignal.login(externalId);
        await OneSignal.User.addTags({
          'user_id': currentUser.id,
          'role': currentUser.role,
          'tenant_id': currentUser.tenantId ?? 'global',
        });
        _ensureOneSignalClickListener();
      } catch (error) {
        debugPrint('No se pudo asociar usuario en OneSignal: $error');
      }
    } else {
      debugPrint(
        'OneSignal pendiente: ejecuta con --dart-define=ONESIGNAL_APP_ID=tu_app_id.',
      );
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
      _onMessageOpenedSubscription ??= FirebaseMessaging.onMessageOpenedApp
          .listen((message) {
            final requestId = _readRequestId(message.data);
            if (requestId != null) {
              _tapHandler?.call(requestId);
            }
          });

      final initialMessage = await messaging.getInitialMessage();
      if (initialMessage != null) {
        final requestId = _readRequestId(initialMessage.data);
        if (requestId != null) {
          _tapHandler?.call(requestId);
        }
      }
    } catch (error) {
      debugPrint('FCM no configurado o no disponible: $error');
    }
  }

  static void _ensureOneSignalClickListener() {
    if (_oneSignalClickListenerReady) {
      return;
    }
    _oneSignalClickListenerReady = true;
    OneSignal.Notifications.addClickListener((event) {
      final requestId = _readRequestId(
        event.notification.additionalData ?? const <String, dynamic>{},
      );
      if (requestId != null) {
        _tapHandler?.call(requestId);
      }
    });
  }

  static int? _readRequestId(Map<String, dynamic> data) {
    final raw =
        data['solicitud_id'] ??
        data['request_id'] ??
        data['solicitudId'] ??
        data['id_solicitud'];
    if (raw == null) {
      return null;
    }
    if (raw is int) {
      return raw;
    }
    return int.tryParse(raw.toString());
  }

  static Future<void> logout() async {
    _tapHandler = null;
    if (kIsWeb) {
      return;
    }

    if (AppConfig.oneSignalAppId.isEmpty) {
      return;
    }

    try {
      await OneSignal.logout();
    } catch (error) {
      debugPrint('No se pudo cerrar sesion de OneSignal: $error');
    }
  }

  static String _buildExternalId(AppUser user) {
    final tenantKey = user.tenantId?.toString() ?? 'global';
    return '$tenantKey:${user.id}';
  }
}
