import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:onesignal_flutter/onesignal_flutter.dart';
import 'package:provider/provider.dart';

import 'src/app_controller.dart';
import 'src/app_config.dart';
import 'src/app_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  if (!kIsWeb && AppConfig.isDevelopment) {
    OneSignal.Debug.setLogLevel(OSLogLevel.verbose);
  }
  if (!kIsWeb && AppConfig.oneSignalAppId.isNotEmpty) {
    OneSignal.initialize(AppConfig.oneSignalAppId);
  }
  runApp(const AsistenciaMecanicaApp());
}

class AsistenciaMecanicaApp extends StatelessWidget {
  const AsistenciaMecanicaApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFFC65A16),
      brightness: Brightness.light,
    );

    return ChangeNotifierProvider(
      create: (_) => AppController()..initialize(),
      child: MaterialApp(
        title: 'Asistencia Mecanica',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: colorScheme,
          scaffoldBackgroundColor: const Color(0xFFF8F4ED),
          cardTheme: CardThemeData(
            color: Colors.white,
            elevation: 0,
            margin: EdgeInsets.zero,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(24),
              side: const BorderSide(color: Color(0xFFE9DED1)),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(18),
              borderSide: const BorderSide(color: Color(0xFFE5D8C9)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(18),
              borderSide: const BorderSide(color: Color(0xFFE5D8C9)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(18),
              borderSide: BorderSide(color: colorScheme.primary, width: 1.4),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          ),
        ),
        home: const AppShell(),
      ),
    );
  }
}
