import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app_controller.dart';
import 'screens/auth_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/report_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/workshop_account_screen.dart';
import 'screens/workshop_home_screen.dart';
import 'screens/workshop_requests_screen.dart';
import 'screens/workshop_team_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;

  int _normalizeIndex(int length) {
    if (length <= 0) {
      return 0;
    }
    return _currentIndex.clamp(0, length - 1);
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    if (!controller.initialized) {
      _currentIndex = 0;
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
                  'Preparando aplicacion mobile...',
                  style: TextStyle(color: Colors.white, fontSize: 16),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (!controller.isAuthenticated) {
      _currentIndex = 0;
      return const AuthScreen();
    }

    if (controller.isWorkshopLike) {
      final pages = [
        WorkshopHomeScreen(
          onOpenCases: () => setState(() => _currentIndex = 1),
          onOpenTeam: () => setState(() => _currentIndex = 2),
          onOpenAccount: () => setState(() => _currentIndex = 3),
        ),
        const WorkshopRequestsScreen(),
        WorkshopTeamScreen(
          onOpenAccount: () => setState(() => _currentIndex = 3),
        ),
        const WorkshopAccountScreen(),
      ];
      final selectedIndex = _normalizeIndex(pages.length);

      return Scaffold(
        body: IndexedStack(index: selectedIndex, children: pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: selectedIndex,
          onDestinationSelected: (index) =>
              setState(() => _currentIndex = index),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_work_outlined),
              label: 'Inicio',
            ),
            NavigationDestination(
              icon: Icon(Icons.assignment_outlined),
              label: 'Casos',
            ),
            NavigationDestination(
              icon: Icon(Icons.groups_outlined),
              label: 'Equipo',
            ),
            NavigationDestination(
              icon: Icon(Icons.manage_accounts_outlined),
              label: 'Cuenta',
            ),
          ],
        ),
      );
    }

    final pages = [
      OverviewScreen(onCreateReport: () => setState(() => _currentIndex = 1)),
      const ReportScreen(),
      const SettingsScreen(),
      ];
    final selectedIndex = _normalizeIndex(pages.length);

    return Scaffold(
      body: IndexedStack(index: selectedIndex, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: selectedIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            label: 'Inicio',
          ),
          NavigationDestination(
            icon: Icon(Icons.sos_outlined),
            label: 'Reportar',
          ),
          NavigationDestination(
            icon: Icon(Icons.tune_outlined),
            label: 'Config',
          ),
        ],
      ),
    );
  }
}
