import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import '../services/realtime_service.dart';
import '../widgets/vehicle_history_card.dart';

class RequestDetailScreen extends StatefulWidget {
  const RequestDetailScreen({super.key, required this.requestId});

  final int requestId;

  @override
  State<RequestDetailScreen> createState() => _RequestDetailScreenState();
}

class _RequestDetailScreenState extends State<RequestDetailScreen> {
  StreamSubscription<RealtimeEvent>? _wsSub;
  String? _lastEvent;
  double? _trackingLat;
  double? _trackingLng;

  int get requestId => widget.requestId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _hookRealtime();
      context.read<AppController>().loadCotizaciones(widget.requestId);
    });
  }

  void _hookRealtime() {
    if (!mounted) return;
    final ctrl = context.read<AppController>();
    if (!ctrl.isAuthenticated) return;
    _wsSub = ctrl.realtime.subscribe('solicitud', widget.requestId).listen((
      ev,
    ) {
      if (!mounted) return;
      setState(() => _lastEvent = ev.event);
      if (ev.event == 'tracking.update' && ev.payload is Map) {
        final payload = ev.payload as Map;
        final lat = _readDouble(payload['latitud']);
        final lng = _readDouble(payload['longitud']);
        if (lat != null && lng != null) {
          setState(() {
            _trackingLat = lat;
            _trackingLng = lng;
          });
        }
      }
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(
          duration: const Duration(seconds: 2),
          content: Text('Actualización en vivo: ${ev.event}'),
        ),
      );
      if (ev.event == 'solicitud.actualizada' ||
          ev.event == 'cotizacion.aceptada' ||
          ev.event == 'cotizacion.nueva' ||
          ev.event == 'tracking.update') {
        ctrl.refreshData();
        ctrl.loadCotizaciones(widget.requestId);
      }
      // ignore: unused_field
      _lastEvent;
    });
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    super.dispose();
  }

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
    final cotizaciones = controller.cotizacionesFor(request.id);
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
              title: 'Seguimiento en mapa',
              child: _LiveMap(
                incidentLat: request.latitud,
                incidentLng: request.longitud,
                mechanicLat: _trackingLat,
                mechanicLng: _trackingLng,
              ),
            ),
            const SizedBox(height: 14),
            if (request.vehiculoId != null) ...[
              VehicleHistoryCard(vehicleId: request.vehiculoId!),
              const SizedBox(height: 14),
            ],
            if (request.estado == 'pendiente' ||
                request.estado == 'buscando_taller' ||
                cotizaciones.isNotEmpty) ...[
              _SectionCard(
                title: 'Cotizaciones de talleres',
                child: cotizaciones.isEmpty
                    ? const Text(
                        'Aun no llegaron cotizaciones. Te avisaremos cuando un taller responda.',
                        style: TextStyle(color: Color(0xFF6F655B)),
                      )
                    : Column(
                        children: cotizaciones
                            .map(
                              (cotizacion) => _CotizacionTile(
                                cotizacion: cotizacion,
                                onSelect: cotizacion.disponible
                                    ? () => _selectCotizacion(
                                        context,
                                        controller,
                                        cotizacion,
                                      )
                                    : null,
                              ),
                            )
                            .toList(),
                      ),
              ),
              const SizedBox(height: 14),
            ],
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
              title: 'Analisis IA',
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
                            label: 'Estado de pago',
                            value: request.paymentReady
                                ? 'Pago QR disponible'
                                : 'Se habilitara cuando el mecanico este en camino o finalice el trabajo',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Escanea el QR, realiza el pago con el monto definido por el taller y confirma la transaccion.',
                    style: TextStyle(
                      color: Color(0xFF6F655B),
                      fontSize: 12,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: request.paymentReady
                        ? () => _showPaymentQr(context, controller, request)
                        : null,
                    icon: const Icon(Icons.payment_outlined),
                    label: const Text('Pagar por QR'),
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
                      : () =>
                            _confirmCancelRequest(context, controller, request),
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
                    'Los adjuntos enviados quedan disponibles para el taller y el mecanico asignado.',
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

  double? _readDouble(dynamic value) {
    if (value is int) return value.toDouble();
    if (value is double) return value;
    return double.tryParse(value?.toString() ?? '');
  }

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

  void _showPaymentQr(
    BuildContext context,
    AppController controller,
    EmergencyRequest request,
  ) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Pago QR - Servicio #${request.id}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: Image.asset(
                'assets/payment_qr.jpeg',
                width: 220,
                height: 220,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              request.precioCobrado == null
                  ? 'Monto definido por el taller'
                  : 'Monto: Bs ${request.precioCobrado!.toStringAsFixed(2)}',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              'Referencia: Solicitud #${request.id}',
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cerrar'),
          ),
          FilledButton(
            onPressed: controller.loading
                ? null
                : () async {
                    await controller.payRequest(
                      request.id,
                      amount: request.precioCobrado,
                    );
                    if (dialogContext.mounted) {
                      Navigator.of(dialogContext).pop();
                    }
                  },
            child: const Text('Confirmar pago'),
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

  Future<void> _selectCotizacion(
    BuildContext context,
    AppController controller,
    Cotizacion cotizacion,
  ) async {
    try {
      await controller.selectCotizacion(cotizacion);
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Cotizacion de ${cotizacion.tallerNombre ?? "taller"} seleccionada.',
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

class _CotizacionTile extends StatelessWidget {
  const _CotizacionTile({required this.cotizacion, required this.onSelect});

  final Cotizacion cotizacion;
  final VoidCallback? onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  cotizacion.tallerNombre ?? 'Taller #${cotizacion.tallerId}',
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ),
              Text(
                'Bs ${cotizacion.costoEstimado.toStringAsFixed(2)}',
                style: const TextStyle(
                  color: Color(0xFF8D5524),
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(label: Text('Llega en ${cotizacion.etaLlegadaMinutos} min')),
              Chip(
                label: Text(
                  '${cotizacion.tiempoReparacionHoras.toStringAsFixed(1)} h reparacion',
                ),
              ),
              if (cotizacion.garantiaDias > 0)
                Chip(label: Text('${cotizacion.garantiaDias} dias garantia')),
            ],
          ),
          if ((cotizacion.descripcion ?? '').trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              cotizacion.descripcion!.trim(),
              style: const TextStyle(color: Color(0xFF6F655B), height: 1.35),
            ),
          ],
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonalIcon(
              onPressed: onSelect,
              icon: const Icon(Icons.check_circle_outline),
              label: Text(
                cotizacion.disponible ? 'Elegir este taller' : 'No disponible',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveMap extends StatelessWidget {
  const _LiveMap({
    required this.incidentLat,
    required this.incidentLng,
    this.mechanicLat,
    this.mechanicLng,
  });

  final double incidentLat;
  final double incidentLng;
  final double? mechanicLat;
  final double? mechanicLng;

  @override
  Widget build(BuildContext context) {
    final incident = LatLng(incidentLat, incidentLng);
    final mechanic = mechanicLat == null || mechanicLng == null
        ? null
        : LatLng(mechanicLat!, mechanicLng!);
    final center = mechanic ?? incident;

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: SizedBox(
        height: 260,
        child: FlutterMap(
          options: MapOptions(
            initialCenter: center,
            initialZoom: mechanic == null ? 14 : 12,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.rutasos.mobile',
            ),
            if (mechanic != null)
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: [mechanic, incident],
                    strokeWidth: 4,
                    color: const Color(0xFF8D5524),
                  ),
                ],
              ),
            MarkerLayer(
              markers: [
                Marker(
                  point: incident,
                  width: 42,
                  height: 42,
                  child: const Icon(
                    Icons.sos_outlined,
                    color: Color(0xFFB3261E),
                    size: 34,
                  ),
                ),
                if (mechanic != null)
                  Marker(
                    point: mechanic,
                    width: 42,
                    height: 42,
                    child: const Icon(
                      Icons.engineering,
                      color: Color(0xFF2E7D32),
                      size: 34,
                    ),
                  ),
              ],
            ),
            if (mechanic == null)
              Positioned(
                left: 12,
                right: 12,
                bottom: 12,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.92),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Padding(
                    padding: EdgeInsets.all(10),
                    child: Text(
                      'Cuando el mecanico comparta su ubicacion, aparecera aqui en tiempo real.',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
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
