import 'dart:io';

import 'package:flutter/foundation.dart';

enum AppEnvironment { dev, prod }

class AppConfig {
  AppConfig._();

  static const _appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'dev');
  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const oneSignalAppId = String.fromEnvironment('ONESIGNAL_APP_ID');
  static const legacyCloudBaseUrl =
      'https://backend-958497253028.europe-west1.run.app';

  static AppEnvironment get environment =>
      _appEnv.toLowerCase() == 'prod'
      ? AppEnvironment.prod
      : AppEnvironment.dev;

  static bool get isProduction => environment == AppEnvironment.prod;
  static bool get isDevelopment => !isProduction;

  static String get defaultBaseUrl {
    final configured = _configuredBaseUrl.trim();
    if (configured.isNotEmpty) {
      return normalizeBaseUrl(configured);
    }

    if (isProduction) {
      return legacyCloudBaseUrl;
    }

    return _platformDevelopmentBaseUrl();
  }

  static String resolveStoredBaseUrl(String? storedBaseUrl) {
    final configured = _configuredBaseUrl.trim();
    if (configured.isNotEmpty) {
      return normalizeBaseUrl(configured);
    }

    if (isProduction) {
      return defaultBaseUrl;
    }

    final candidate = storedBaseUrl == legacyCloudBaseUrl
        ? defaultBaseUrl
        : (storedBaseUrl ?? defaultBaseUrl);
    return normalizeBaseUrl(candidate);
  }

  static String normalizeBaseUrl(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) {
      return defaultBaseUrl;
    }

    final normalized = trimmed.endsWith('/')
        ? trimmed.substring(0, trimmed.length - 1)
        : trimmed;

    if (isProduction) {
      return normalized;
    }

    if (normalized == 'http://localhost:8000' ||
        normalized == 'http://127.0.0.1:8000') {
      return _isAndroidRuntime()
          ? 'http://10.0.2.2:8000'
          : 'http://localhost:8000';
    }

    if (normalized == 'http://10.0.2.2:8000' && !_isAndroidRuntime()) {
      return 'http://localhost:8000';
    }

    return normalized;
  }

  static String _platformDevelopmentBaseUrl() {
    if (_isAndroidRuntime()) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://localhost:8000';
  }

  static bool _isAndroidRuntime() {
    if (kIsWeb) {
      return false;
    }
    try {
      return Platform.isAndroid;
    } catch (_) {
      return false;
    }
  }
}
