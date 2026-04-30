import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class RequestDetailScreen extends StatelessWidget {
  const RequestDetailScreen({super.key, required this.requestId});

  final int requestId;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final request = _findRequest(controller.requests, requestId);
    if (request == null) {
      return Scaffold(
        appBar: AppBar(title: Text('Solicitud #$requestId')),
        body: const Center(
          child: Text('Solicitud no disponible. Actualiza el seguimiento.'),
        ),
      );
    }
    final meta = controller.metaFor(request.id);
    final vehicleLabel = controller.vehicleLabelFor(request);
    final technicianLabel = controller.technicianLabelFor(request);
    final workshopLabel = controller.workshopLabelFor(request);
    final formatter = DateFormat('dd/MM/yyyy - HH:mm');

    return Scaffold(
      appBar: AppBar(
        title: Text('Solicitud #${request.id}'),
        actions: [
          IconButton(
            tooltip: 'Actualizar estado',
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
              title: 'Estado actual',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatusPill(
                    status: request.estado,
                    label: request.statusLabel,
                  ),
                  const SizedBox(height: 14),
                  _InfoLine(label: 'Vehiculo', value: vehicleLabel),
                  _InfoLine(
                    label: 'Fecha',
                    value: formatter.format(request.fechaCreacion.toLocal()),
                  ),
                  _InfoLine(
                    label: 'Ubicacion',
                    value:
                        '${request.latitud.toStringAsFixed(6)}, ${request.longitud.toStringAsFixed(6)}',
                  ),
                  _InfoLine(label: 'Taller asignado', value: workshopLabel),
                  _InfoLine(label: 'Tecnico asignado', value: technicianLabel),
                  _InfoLine(
                    label: 'Tiempo estimado',
                    value: request.tiempoEstimadoMinutos == null
                        ? 'Pendiente'
                        : '${request.tiempoEstimadoMinutos} min',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Descripcion del incidente',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _InfoLine(
                    label: 'Tipo reportado',
                    value: meta?.issueType ?? 'No registrado',
                  ),
                  _InfoLine(
                    label: 'Descripcion enviada',
                    value: request.descripcion,
                  ),
                  _InfoLine(
                    label: 'Notas adicionales',
                    value: meta?.extraNotes.trim().isEmpty ?? true
                        ? 'Sin notas adicionales'
                        : meta!.extraNotes,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Analisis del backend',
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
                ],
              ),
            ),
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Pago del servicio',
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
                            label: 'Monto estimado',
                            value: request.precioCobrado == null
                                ? 'El taller aun no definio el monto'
                                : 'Bs ${request.precioCobrado!.toStringAsFixed(2)}',
                          ),
                          _InfoLine(
                            label: 'Estado de checkout',
                            value: request.paymentReady
                                ? 'Listo para integrar pasarela'
                                : 'Se habilitara cuando el tecnico este en camino o finalice el trabajo',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Este es el espacio donde se conectara la pasarela real. Tu companero solo tendra que enlazar el proveedor y la confirmacion del pago.',
                    style: TextStyle(
                      color: Color(0xFF6F655B),
                      fontSize: 12,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: () => _showPaymentPlaceholder(context),
                    icon: const Icon(Icons.payment_outlined),
                    label: const Text('Ver checkout preparado'),
                  ),
                ],
              ),
            ),
            if (request.canBeCancelled) ...[
              const SizedBox(height: 14),
              _SectionCard(
                title: 'Acciones',
                child: FilledButton.tonalIcon(
                  style: FilledButton.styleFrom(
                    foregroundColor: const Color(0xFFA22C29),
                  ),
                  onPressed: controller.loading
                      ? null
                      : () => _confirmCancelRequest(
                            context,
                            controller,
                            request,
                          ),
                  icon: const Icon(Icons.cancel_outlined),
                  label: const Text('Cancelar solicitud'),
                ),
              ),
            ],
            const SizedBox(height: 14),
            _SectionCard(
              title: 'Adjuntos mobile',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _AttachmentSummary(
                    icon: Icons.photo_library_outlined,
                    title: 'Fotografias',
                    value: '${meta?.imagePaths.length ?? 0} archivo(s)',
                    items: meta?.imagePaths ?? const [],
                  ),
                  const SizedBox(height: 12),
                  _AttachmentSummary(
                    icon: Icons.mic_none_outlined,
                    title: 'Audio descriptivo',
                    value: meta?.audioPath == null
                        ? 'Sin audio'
                        : _fileName(meta!.audioPath!),
                    items: meta?.audioPath == null
                        ? const []
                        : [meta!.audioPath!],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Los adjuntos se conservan localmente mientras el backend no tenga carga de archivos.',
                    style: TextStyle(
                      color: Color(0xFF6F655B),
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _fileName(String path) => path.split(RegExp(r'[\\/]')).last;

  EmergencyRequest? _findRequest(
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

  void _showPaymentPlaceholder(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Checkout pendiente'),
        content: const Text(
          'Aqui se abrira la pasarela cuando el proveedor real este conectado. La interfaz ya esta reservada para ese paso.',
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

  Future<void> _confirmCancelRequest(
    BuildContext context,
    AppController controller,
    EmergencyRequest request,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Cancelar solicitud'),
        content: const Text(
          'Esta accion avisara a los talleres involucrados y detendra el seguimiento de la solicitud.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Volver'),
          ),
          FilledButton.tonal(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Cancelar solicitud'),
          ),
        ],
      ),
    );

    if (confirmed != true || !context.mounted) {
      return;
    }

    try {
      await controller.cancelRequest(request.id);
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Solicitud #${request.id} cancelada.')),
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

class _AttachmentSummary extends StatelessWidget {
  const _AttachmentSummary({
    required this.icon,
    required this.title,
    required this.value,
    required this.items,
  });

  final IconData icon;
  final String title;
  final String value;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
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
            Row(
              children: [
                Icon(icon, color: const Color(0xFFC65A16)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text(value, style: const TextStyle(color: Color(0xFF6F655B))),
              ],
            ),
            if (items.isNotEmpty) ...[
              const SizedBox(height: 10),
              ...items.map(
                (path) => Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    path.split(RegExp(r'[\\/]')).last,
                    style: const TextStyle(
                      color: Color(0xFF5F554B),
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
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
