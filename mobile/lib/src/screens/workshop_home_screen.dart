import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class WorkshopHomeScreen extends StatelessWidget {
  const WorkshopHomeScreen({
    super.key,
    required this.onOpenCases,
    required this.onOpenTeam,
    required this.onOpenAccount,
  });

  final VoidCallback onOpenCases;
  final VoidCallback onOpenTeam;
  final VoidCallback onOpenAccount;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final profile = controller.workshopProfile;
    final stats = controller.workshopStats;
    final managed = controller.workshopManagedRequests;
    final activeManaged = managed.where((request) => !request.isClosed).length;
    final inboxCount = controller.workshopInboxRequests.length;

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: controller.refreshData,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          children: [
            _HeroCard(
              title:
                  profile?.nombreComercial ??
                  controller.currentUser?.displayName ??
                  'Taller mobile',
              subtitle: profile == null
                  ? 'Completa el perfil del taller para operar desde el telefono.'
                  : 'Control rapido del taller, servicios y equipo sin depender de una PC.',
              actions: [
                _HeroAction(label: 'Casos', onTap: onOpenCases),
                _HeroAction(label: 'Equipo', onTap: onOpenTeam),
                _HeroAction(label: 'Cuenta', onTap: onOpenAccount),
              ],
            ),
            const SizedBox(height: 16),
            if (profile == null)
              Card(
                color: const Color(0xFFFFF3E6),
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Falta registrar el taller',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'La autenticacion ya funciona, pero para asignar tecnicos y tomar servicios primero debes guardar el perfil comercial del taller en la pestana Cuenta.',
                        style: TextStyle(height: 1.5),
                      ),
                      const SizedBox(height: 14),
                      FilledButton(
                        onPressed: onOpenAccount,
                        child: const Text('Completar perfil'),
                      ),
                    ],
                  ),
                ),
              ),
            if (profile == null) const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    label: 'Bandeja',
                    value: '$inboxCount',
                    caption: 'Casos visibles para este taller',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    label: 'Activos',
                    value: '$activeManaged',
                    caption: 'Servicios tomados por el taller',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    label: 'Tecnicos libres',
                    value: '${controller.availableTechniciansCount}',
                    caption:
                        '${controller.technicians.length} tecnico(s) registrados',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    label: 'Cobro listo',
                    value: '${controller.paymentReadyCount}',
                    caption: 'Servicios donde ya puede abrirse checkout',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            if (stats != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Resumen operativo',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 14),
                      _InfoRow(
                        label: 'Calificacion promedio',
                        value: stats.workshopRating.toStringAsFixed(1),
                      ),
                      _InfoRow(
                        label: 'Servicios completados',
                        value: '${stats.totalCompleted}',
                      ),
                      _InfoRow(
                        label: 'Ingreso promedio',
                        value: stats.averageIncome == 0
                            ? 'Sin datos'
                            : 'Bs ${stats.averageIncome.toStringAsFixed(2)}',
                      ),
                      _InfoRow(
                        label: 'Comisiones acumuladas',
                        value: stats.totalCommissions == 0
                            ? 'Sin datos'
                            : 'Bs ${stats.totalCommissions.toStringAsFixed(2)}',
                      ),
                      _InfoRow(
                        label: 'Tiempo respuesta',
                        value: stats.averageResponseMinutes == null
                            ? 'Sin datos'
                            : '${stats.averageResponseMinutes} min',
                      ),
                    ],
                  ),
                ),
              ),
            if (stats != null) const SizedBox(height: 18),
            const Text(
              'Ultimos casos visibles',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
            ),
            const SizedBox(height: 12),
            if (controller.workshopInboxRequests.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'Todavia no hay servicios visibles para este taller.',
                    style: TextStyle(color: Color(0xFF6F655B)),
                  ),
                ),
              )
            else
              ...controller.workshopInboxRequests
                  .take(3)
                  .map(
                    (request) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _RequestPreviewCard(
                        request: request,
                        onTap: onOpenCases,
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }

}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.title,
    required this.subtitle,
    required this.actions,
  });

  final String title;
  final String subtitle;
  final List<_HeroAction> actions;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1F1A16), Color(0xFF4E311F), Color(0xFFC65A16)],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Operacion movil del taller',
              style: TextStyle(
                color: Color(0xFFFADBBE),
                fontSize: 12,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.4,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 30,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              subtitle,
              style: const TextStyle(color: Color(0xFFF8EBDD), height: 1.5),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: actions
                  .map(
                    (action) => FilledButton.tonal(
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.white.withValues(alpha: 0.18),
                        foregroundColor: Colors.white,
                      ),
                      onPressed: action.onTap,
                      child: Text(action.label),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroAction {
  const _HeroAction({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.caption,
  });

  final String label;
  final String value;
  final String caption;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              caption,
              style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF6F655B)),
            ),
          ),
          const SizedBox(width: 12),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _RequestPreviewCard extends StatelessWidget {
  const _RequestPreviewCard({required this.request, required this.onTap});

  final EmergencyRequest request;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Solicitud #${request.id}',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: _statusColor(
                        request.estado,
                      ).withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      child: Text(
                        request.statusLabel,
                        style: TextStyle(
                          color: _statusColor(request.estado),
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                request.resumenIa ?? request.descripcion,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(height: 1.45, color: Color(0xFF5F554B)),
              ),
              const SizedBox(height: 10),
              Text(
                '${request.latitud.toStringAsFixed(4)}, ${request.longitud.toStringAsFixed(4)}',
                style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Color _statusColor(String status) {
  switch (status) {
    case 'pendiente':
      return const Color(0xFF9C5C00);
    case 'asignada':
      return const Color(0xFF0F5CBD);
    case 'en_progreso':
      return const Color(0xFF6E46C2);
    case 'resuelta':
      return const Color(0xFF167B47);
    case 'cancelada':
      return const Color(0xFFA22C29);
    default:
      return const Color(0xFF5F554B);
  }
}
