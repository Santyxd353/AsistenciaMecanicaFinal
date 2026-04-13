import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app_controller.dart';
import 'screens/auth_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/report_screen.dart';
import 'screens/settings_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    if (!controller.initialized) {
      return Scaffold(
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xFF1E1B18), Color(0xFFC65A16)],
            ),
          ),
          child: const Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(color: Colors.white),
                SizedBox(height: 18),
                Text(
                  'Preparando cliente mobile...',
                  style: TextStyle(color: Colors.white, fontSize: 16),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (!controller.isAuthenticated) {
      return const AuthScreen();
    }

    if (!controller.isDriver) {
      return const SettingsScreen(workshopMode: true);
    }

    final pages = [
      OverviewScreen(onCreateReport: () => setState(() => _currentIndex = 1)),
      const ReportScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Inicio'),
          NavigationDestination(icon: Icon(Icons.sos_outlined), label: 'Reportar'),
          NavigationDestination(icon: Icon(Icons.tune_outlined), label: 'Config'),
        ],
      ),
    );
  }
}
