import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class WorkshopRequestDetailScreen extends StatelessWidget {
  const WorkshopRequestDetailScreen({super.key, required this.requestId});

  final int requestId;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final request = _findRequest(controller.requests, requestId);

    if (request == null) {
      return Scaffold(
        appBar: AppBar(title: Text('Solicitud #$requestId')),
        body: const Center(
          child: Text('La solicitud ya no esta visible. Actualiza la bandeja.'),
        ),
      );
    }

    final formatter = DateFormat('dd/MM/yyyy - HH:mm');
    final availableTechnicians =
        controller.technicians
            .where((technician) => technician.disponible)
            .toList()
          ..sort((left, right) => left.nombre.compareTo(right.nombre));

    return Scaffold(
      appBar: AppBar(
        title: Text('Solicitud #${request.id}'),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: controller.loading ? null : controller.refreshData,
            icon: const Icon(Icons.sync),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: controller.refreshData,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          children: [
            _SectionCard(
              title: 'Estado operativo',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatusPill(
                    status: request.estado,
                    label: request.statusLabel,
                  ),
                  const SizedBox(height: 14),
                  _InfoLine(
                    label: 'Fecha',
                    value: formatter.format(request.fechaCreacion.toLocal()),
                  ),
                  _InfoLine(
                    label: 'Taller',
                    value: controller.workshopLabelFor(request),
                  ),
                  _InfoLine(
                    label: 'Tecnico',
                    value: controller.technicianLabelFor(request),
                  ),
                  _InfoLine(
                    label: 'Ubicacion',
                    value:
                        '${request.latitud.toStringAsFixed(6)}, ${request.longitud.toStringAsFixed(6)}',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Incidente reportado',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _InfoLine(
                    label: 'Clasificacion IA',
                    value: request.clasificacionIa ?? 'Sin clasificar',
                  ),
                  _InfoLine(
                    label: 'Prioridad',
                    value: request.prioridadIa ?? 'Sin prioridad',
                  ),
                  _InfoLine(
                    label: 'Resumen',
                    value: request.resumenIa ?? 'Sin resumen',
                  ),
                  _InfoLine(label: 'Descripcion', value: request.descripcion),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Cobro del servicio',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFFAF5),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: const Color(0xFFF0E5D7)),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _InfoLine(
                            label: 'Monto referencial',
                            value: request.precioCobrado == null
                                ? 'Pendiente de definir'
                                : 'Bs ${request.precioCobrado!.toStringAsFixed(2)}',
                          ),
                          _InfoLine(
                            label: 'Comision plataforma',
                            value: request.comisionPlataforma == null
                                ? 'Pendiente de calcular'
                                : 'Bs ${request.comisionPlataforma!.toStringAsFixed(2)}',
                          ),
                          _InfoLine(
                            label: 'Estado de integracion',
                            value: request.paymentReady
                                ? 'Listo para abrir checkout externo'
                                : 'Esperando que el tecnico vaya en camino o cierre el servicio',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Aqui ira la pasarela real. La app ya define el momento visual del cobro; falta conectar el proveedor, la confirmacion y los estados finales del pago.',
                    style: TextStyle(color: Color(0xFF6F655B), height: 1.5),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: () => _showGatewayPlaceholder(context),
                    icon: const Icon(Icons.payment_outlined),
                    label: const Text('Abrir interfaz de pago'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _ActionPanel(
              request: request,
              availableTechnicians: availableTechnicians,
            ),
          ],
        ),
      ),
    );
  }

  static EmergencyRequest? _findRequest(
    List<EmergencyRequest> requests,
    int requestId,
  ) {
    for (final request in requests) {
      if (request.id == requestId) {
        return request;
      }
    }
    return null;
  }

  static void _showGatewayPlaceholder(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Pasarela pendiente'),
        content: const Text(
          'Este boton ya representa el punto donde tu companero debe abrir el checkout real. La interfaz esta lista; solo falta conectar el proveedor de pagos.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }
}

class _ActionPanel extends StatelessWidget {
  const _ActionPanel({
    required this.request,
    required this.availableTechnicians,
  });

  final EmergencyRequest request;
  final List<Technician> availableTechnicians;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    return _SectionCard(
      title: 'Acciones',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (request.tallerId == null &&
              controller.canWorkshopTakeRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => _pickTechnicianAndAssign(context, controller),
              icon: const Icon(Icons.engineering_outlined),
              label: const Text('Tomar servicio y asignar tecnico'),
            ),
          if (request.estado == 'asignada' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'en_progreso',
                    ),
              icon: const Icon(Icons.route_outlined),
              label: const Text('Marcar tecnico en camino'),
            ),
          if (request.estado == 'en_progreso' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'resuelta',
                    ),
              icon: const Icon(Icons.task_alt_outlined),
              label: const Text('Marcar servicio finalizado'),
            ),
          if (!request.isClosed &&
              controller.canWorkshopManageRequest(request)) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'cancelada',
                    ),
              icon: const Icon(Icons.cancel_outlined),
              label: const Text('Cancelar solicitud'),
            ),
          ],
          if (request.tallerId == null && availableTechnicians.isEmpty) ...[
            const SizedBox(height: 12),
            const Text(
              'No hay tecnicos disponibles para tomar este servicio.',
              style: TextStyle(color: Color(0xFF6F655B)),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _pickTechnicianAndAssign(
    BuildContext context,
    AppController controller,
  ) async {
    if (availableTechnicians.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Primero deja al menos un tecnico disponible.'),
        ),
      );
      return;
    }

    final selected = await showModalBottomSheet<Technician>(
      context: context,
      showDragHandle: true,
      builder: (dialogContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Selecciona un tecnico',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
              ),
              const SizedBox(height: 12),
              ...availableTechnicians.map(
                (technician) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const CircleAvatar(
                    child: Icon(Icons.person_outline),
                  ),
                  title: Text(technician.nombre),
                  subtitle: Text(technician.especialidad),
                  onTap: () => Navigator.of(dialogContext).pop(technician),
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (selected == null) {
      return;
    }

    try {
      await controller.assignRequest(request: request, technician: selected);
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Solicitud #${request.id} asignada a ${selected.nombre}.',
          ),
        ),
      );
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600, height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status, required this.label});

  final String status;
  final String label;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'pendiente' => const Color(0xFF9C5C00),
      'asignada' => const Color(0xFF0F5CBD),
      'en_progreso' => const Color(0xFF6E46C2),
      'resuelta' => const Color(0xFF167B47),
      'cancelada' => const Color(0xFFA22C29),
      _ => const Color(0xFF5F554B),
    };

    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          label,
          style: TextStyle(color: color, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
