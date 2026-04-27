import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import 'request_detail_screen.dart';

class OverviewScreen extends StatelessWidget {
  const OverviewScreen({
    super.key,
    required this.onCreateReport,
    required this.onRegisterVehicle,
  });

  final VoidCallback onCreateReport;
  final VoidCallback onRegisterVehicle;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final requests = controller.requests;
    final notifications = controller.notifications.take(4).toList();
    final activeCount = controller.activeRequests.length;
    final closedCount = requests.length - activeCount;

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: controller.refreshData,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          children: [
            _HeroCard(
              user: controller.currentUser,
              vehicleCount: controller.vehicles.length,
              activeCount: activeCount,
              onCreateReport: onCreateReport,
              onRegisterVehicle: onRegisterVehicle,
            ),
            const SizedBox(height: 16),
            if (controller.currentUser == null || controller.vehicles.isEmpty)
              _SetupWarning(
                missingProfile: controller.currentUser == null,
                missingVehicles: controller.vehicles.isEmpty,
                onRegisterVehicle: onRegisterVehicle,
              ),
            if (controller.currentUser == null || controller.vehicles.isEmpty)
              const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    title: 'Seguimiento',
                    value: requests.length.toString(),
                    caption: 'Solicitudes creadas desde mobile',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    title: 'Activas',
                    value: activeCount.toString(),
                    caption: 'Pendientes o en proceso',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    title: 'Cerradas',
                    value: closedCount.toString(),
                    caption: 'Resueltas o canceladas',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(
              'Mis emergencias',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: controller.loading ? null : controller.refreshData,
              icon: const Icon(Icons.sync),
              label: const Text('Actualizar estados'),
            ),
            const SizedBox(height: 10),
            if (controller.loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (requests.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Todavia no registraste ninguna solicitud.',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Desde la pestana Reportar puedes enviar ubicacion, descripcion, fotos y audio para que el sistema procese la solicitud.',
                      ),
                      const SizedBox(height: 18),
                      FilledButton.icon(
                        onPressed: onCreateReport,
                        icon: const Icon(Icons.add_location_alt_outlined),
                        label: const Text('Crear primer reporte'),
                      ),
                    ],
                  ),
                ),
              )
            else
              ...requests.map(
                (request) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _RequestCard(
                    request: request,
                    vehicleLabel: controller.vehicleLabelFor(request),
                    etaLabel: controller.etaLabelFor(request),
                    paymentLabel: controller.paymentLabelFor(request),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) =>
                              RequestDetailScreen(requestId: request.id),
                        ),
                      );
                    },
                  ),
                ),
              ),
            if (notifications.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(
                'Novedades recientes',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 10),
              ...notifications.map(
                (notification) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _NotificationCard(notification: notification),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.user,
    required this.vehicleCount,
    required this.activeCount,
    required this.onCreateReport,
    required this.onRegisterVehicle,
  });

  final AppUser? user;
  final int vehicleCount;
  final int activeCount;
  final VoidCallback onCreateReport;
  final VoidCallback onRegisterVehicle;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1F1A16), Color(0xFF5F2E14), Color(0xFFC65A16)],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              user?.displayName ?? 'Conductor invitado',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              activeCount == 0
                  ? 'Listo para reportar una nueva emergencia.'
                  : 'Tienes $activeCount atencion(es) en seguimiento dentro del sistema.',
              style: const TextStyle(color: Color(0xFFF9EDE0), height: 1.4),
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _HeroTag(
                  icon: Icons.directions_car_filled_outlined,
                  label: '$vehicleCount vehiculo(s)',
                ),
                _HeroTag(
                  icon: Icons.bolt_outlined,
                  label: '$activeCount alerta(s) activas',
                ),
              ],
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: const Color(0xFF5F2E14),
              ),
              onPressed: onCreateReport,
              icon: const Icon(Icons.sos),
              label: const Text('Reportar emergencia'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(color: Colors.white54),
              ),
              onPressed: onRegisterVehicle,
              icon: const Icon(Icons.directions_car_filled_outlined),
              label: const Text('Registrar vehiculo'),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroTag extends StatelessWidget {
  const _HeroTag({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white24),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: Colors.white),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(color: Colors.white)),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.caption,
  });

  final String title;
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
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
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

class _SetupWarning extends StatelessWidget {
  const _SetupWarning({
    required this.missingProfile,
    required this.missingVehicles,
    required this.onRegisterVehicle,
  });

  final bool missingProfile;
  final bool missingVehicles;
  final VoidCallback onRegisterVehicle;

  @override
  Widget build(BuildContext context) {
    final messages = <String>[
      if (missingProfile)
        'Completa tu perfil local antes de enviar solicitudes.',
      if (missingVehicles)
        'Registra al menos un vehiculo antes de reportar una emergencia.',
    ];

    return Card(
      color: const Color(0xFFFFF3E6),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  color: Color(0xFFC65A16),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    messages.join(' '),
                    style: const TextStyle(height: 1.45),
                  ),
                ),
              ],
            ),
            if (missingVehicles) ...[
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onRegisterVehicle,
                icon: const Icon(Icons.directions_car_filled_outlined),
                label: const Text('Registrar vehiculo'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _RequestCard extends StatelessWidget {
  const _RequestCard({
    required this.request,
    required this.vehicleLabel,
    required this.etaLabel,
    required this.paymentLabel,
    required this.onTap,
  });

  final EmergencyRequest request;
  final String vehicleLabel;
  final String etaLabel;
  final String paymentLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('dd/MM - HH:mm');
    final statusColor = _statusColor(request.estado);

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
                      vehicleLabel,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.15),
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
                          color: statusColor,
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
                request.clasificacionIa ?? 'Emergencia enviada',
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              Text(
                request.resumenIa ?? request.descripcion,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Color(0xFF5F554B), height: 1.4),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  const Icon(
                    Icons.schedule,
                    size: 18,
                    color: Color(0xFF6F655B),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    formatter.format(request.fechaCreacion.toLocal()),
                    style: const TextStyle(color: Color(0xFF6F655B)),
                  ),
                  const SizedBox(width: 16),
                  const Icon(
                    Icons.engineering_outlined,
                    size: 18,
                    color: Color(0xFF6F655B),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      request.tecnicoNombre ??
                          (request.tecnicoId == null
                              ? 'Sin tecnico'
                              : 'Tecnico #${request.tecnicoId}'),
                      style: const TextStyle(color: Color(0xFF6F655B)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _MiniMetaChip(
                    icon: Icons.home_repair_service_outlined,
                    label: request.tallerNombre ?? 'Taller pendiente',
                  ),
                  _MiniMetaChip(
                    icon: Icons.av_timer_outlined,
                    label: etaLabel,
                  ),
                  _MiniMetaChip(
                    icon: Icons.payments_outlined,
                    label: paymentLabel,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(
                    Icons.location_on_outlined,
                    size: 18,
                    color: Color(0xFF6F655B),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      '${request.latitud.toStringAsFixed(4)}, ${request.longitud.toStringAsFixed(4)}',
                      style: const TextStyle(color: Color(0xFF6F655B)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MiniMetaChip extends StatelessWidget {
  const _MiniMetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: const Color(0xFF6F655B)),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(color: Color(0xFF5F554B), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification});

  final AppNotification notification;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('dd/MM - HH:mm');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.notifications_active_outlined, color: Color(0xFFC65A16)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    notification.title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text(
                  formatter.format(notification.createdAt.toLocal()),
                  style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              notification.message,
              style: const TextStyle(color: Color(0xFF5F554B), height: 1.4),
            ),
          ],
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
