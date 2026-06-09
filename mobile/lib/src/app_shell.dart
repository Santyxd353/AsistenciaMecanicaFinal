import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app_controller.dart';
import 'screens/auth_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/quote_request_screen.dart';
import 'screens/report_screen.dart';
import 'screens/request_detail_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/vehicle_registration_screen.dart';
import 'screens/workshop_account_screen.dart';
import 'screens/workshop_home_screen.dart';
import 'screens/workshop_request_detail_screen.dart';
import 'screens/workshop_requests_screen.dart';
import 'screens/workshop_team_screen.dart';
import 'screens/kpi_screen.dart';
import 'widgets/offline_banner.dart';

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

    _openPendingNotificationRequest(controller);

    if (controller.isGlobalAdmin) {
      _currentIndex = 0;
      return const _SuperAdminMobileBlocked();
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
        const KpiScreen(),
      ];
      final selectedIndex = _normalizeIndex(pages.length);

      return Scaffold(
        body: Column(
          children: [
            const OfflineBanner(),
            Expanded(
              child: IndexedStack(index: selectedIndex, children: pages),
            ),
          ],
        ),
        bottomNavigationBar: _RutaNavigationBar(
          selectedIndex: selectedIndex,
          onSelected: (index) => setState(() => _currentIndex = index),
          items: const [
            _RutaNavItem(Icons.home_work_outlined, 'Inicio'),
            _RutaNavItem(Icons.assignment_outlined, 'Casos'),
            _RutaNavItem(Icons.groups_outlined, 'Equipo'),
            _RutaNavItem(Icons.manage_accounts_outlined, 'Cuenta'),
            _RutaNavItem(Icons.bar_chart, 'KPIs'),
          ],
        ),
      );
    }

    if (controller.currentUser?.role == 'tecnico') {
      final pages = [const WorkshopRequestsScreen(), const SettingsScreen()];
      final selectedIndex = _normalizeIndex(pages.length);

      return Scaffold(
        body: Column(
          children: [
            const OfflineBanner(),
            Expanded(
              child: IndexedStack(index: selectedIndex, children: pages),
            ),
          ],
        ),
        bottomNavigationBar: _RutaNavigationBar(
          selectedIndex: selectedIndex,
          onSelected: (index) => setState(() => _currentIndex = index),
          items: const [
            _RutaNavItem(Icons.assignment_outlined, 'Trabajos'),
            _RutaNavItem(Icons.person_outline, 'Cuenta'),
          ],
        ),
      );
    }

    final pages = [
      OverviewScreen(
        onCreateReport: () => setState(() => _currentIndex = 1),
        onRegisterVehicle: () => setState(() => _currentIndex = 3),
      ),
      const ReportScreen(),
      const QuoteRequestScreen(),
      const VehicleRegistrationScreen(),
      const SettingsScreen(),
    ];
    final selectedIndex = _normalizeIndex(pages.length);

    return Scaffold(
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(
            child: IndexedStack(index: selectedIndex, children: pages),
          ),
        ],
      ),
      bottomNavigationBar: _RutaNavigationBar(
        selectedIndex: selectedIndex,
        onSelected: (index) => setState(() => _currentIndex = index),
        items: const [
          _RutaNavItem(Icons.dashboard_outlined, 'Inicio'),
          _RutaNavItem(Icons.sos_outlined, 'Reportar'),
          _RutaNavItem(Icons.request_quote_outlined, 'Cotizar'),
          _RutaNavItem(Icons.directions_car_filled_outlined, 'Vehiculos'),
          _RutaNavItem(Icons.person_outline, 'Perfil'),
        ],
      ),
    );
  }

  void _openPendingNotificationRequest(AppController controller) {
    final requestId = controller.pendingNotificationRequestId;
    if (requestId == null) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final consumed = controller.consumePendingNotificationRequestId();
      if (consumed == null) {
        return;
      }
      final user = controller.currentUser;
      final page = user?.isDriver == true
          ? RequestDetailScreen(requestId: consumed)
          : WorkshopRequestDetailScreen(requestId: consumed);
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
    });
  }
}

class _SuperAdminMobileBlocked extends StatelessWidget {
  const _SuperAdminMobileBlocked();

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF1E1B18), Color(0xFF5C2F16), Color(0xFFF6EBDC)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.desktop_windows_outlined,
                        size: 42,
                        color: Color(0xFF8D5524),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Panel Super Admin solo en PC',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 10),
                      const Text(
                        'La aplicacion movil esta pensada para clientes, administradores de taller y mecanicos. Para ver todos los tenants, reportes globales y auditoria usa el dashboard web.',
                        style: TextStyle(height: 1.5, color: Color(0xFF6F655B)),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: controller.loading
                              ? null
                              : controller.logout,
                          icon: const Icon(Icons.logout),
                          label: const Text('Cerrar sesion'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RutaNavItem {
  const _RutaNavItem(this.icon, this.label);

  final IconData icon;
  final String label;
}

class _RutaNavigationBar extends StatelessWidget {
  const _RutaNavigationBar({
    required this.selectedIndex,
    required this.onSelected,
    required this.items,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<_RutaNavItem> items;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: const Color(0xFFFFF9EF),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: const Color(0xFFD2C4BB)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x1A715A3E),
                blurRadius: 22,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Row(
              children: [
                for (var i = 0; i < items.length; i++)
                  Expanded(
                    child: _RutaNavButton(
                      item: items[i],
                      selected: i == selectedIndex,
                      onTap: () => onSelected(i),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RutaNavButton extends StatelessWidget {
  const _RutaNavButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _RutaNavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        height: 48,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF322214) : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              item.icon,
              size: 19,
              color: selected ? Colors.white : const Color(0xFF715A3E),
            ),
            const SizedBox(height: 2),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 180),
              style: TextStyle(
                color: selected ? Colors.white : const Color(0xFF715A3E),
                fontSize: 10,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              ),
              child: Text(
                item.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
