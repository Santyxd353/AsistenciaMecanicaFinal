import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app_controller.dart';
import '../models.dart';
import '../repositories.dart';
import '../widgets/vehicle_history_card.dart';

class WorkshopRequestDetailScreen extends StatefulWidget {
  const WorkshopRequestDetailScreen({super.key, required this.requestId});

  final int requestId;

  @override
  State<WorkshopRequestDetailScreen> createState() =>
      _WorkshopRequestDetailScreenState();
}

class _WorkshopRequestDetailScreenState
    extends State<WorkshopRequestDetailScreen> {
  int get requestId => widget.requestId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      unawaited(context.read<AppController>().refreshData());
    });
  }

  @override
  void dispose() {
    // Si el técnico cierra esta pantalla, paramos el timer de tracking para
    // no consumir batería ni datos en segundo plano. La pantalla del detalle
    // es el único punto del cual emitimos la ubicación; cuando el mecánico
    // vuelve aquí, el `initState` del próximo render relanza el timer.
    final controller = context.read<AppController>();
    if (controller.trackingRequestId == requestId) {
      controller.stopMechanicTracking();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final request = _findRequest(controller.requests, requestId);

    // Auto-start tracking si quien mira es el mecánico asignado y el estado
    // está en alguno de los activos. Lo hacemos en build (post-frame) para
    // poder reaccionar también a cambios de estado vía realtime.
    if (request != null && controller.currentUser?.role == 'tecnico') {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        const activos = {
          'asignada',
          'tecnico_en_camino',
          'tecnico_llego',
          'en_proceso',
        };
        if (activos.contains(request.estado)) {
          controller.startMechanicTracking(request);
        } else if (controller.trackingRequestId == request.id) {
          controller.stopMechanicTracking();
        }
      });
    }

    if (request == null) {
      return Scaffold(
        appBar: AppBar(title: Text('Solicitud #$requestId')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (controller.loading) ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 16),
                  const Text('Cargando trabajo asignado...'),
                ] else ...[
                  const Icon(Icons.assignment_late_outlined, size: 44),
                  const SizedBox(height: 12),
                  const Text(
                    'No se pudo cargar este trabajo.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Actualiza la bandeja. Si sigue sin aparecer, el taller todavia no asigno este servicio a tu usuario mecanico.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: controller.refreshData,
                    icon: const Icon(Icons.sync),
                    label: const Text('Actualizar'),
                  ),
                ],
              ],
            ),
          ),
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
                  if (request.audioResumenIa?.trim().isNotEmpty ?? false)
                    _InfoLine(
                      label: 'Resumen IA del audio',
                      value: request.audioResumenIa!.trim(),
                    ),
                  if (request.audioUrl?.trim().isNotEmpty ?? false)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: OutlinedButton.icon(
                        onPressed: () =>
                            _openAudio(context, controller, request),
                        icon: const Icon(Icons.play_circle_outline),
                        label: const Text('Escuchar audio del cliente'),
                      ),
                    ),
                  _InfoLine(label: 'Descripcion', value: request.descripcion),
                  if (request.rutaRecomendadaIa?.trim().isNotEmpty ?? false)
                    _InfoLine(
                      label: 'Ruta sugerida',
                      value: request.rutaRecomendadaIa!.trim(),
                    ),
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: OutlinedButton.icon(
                      onPressed: () => _openRoute(request),
                      icon: const Icon(Icons.map_outlined),
                      label: const Text('Abrir ruta en mapas'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (request.vehiculoId != null) ...[
              VehicleHistoryCard(
                vehicleId: request.vehiculoId!,
                title: 'Historia clinica del vehiculo',
              ),
              const SizedBox(height: 14),
            ],
            if (controller.currentUser?.role == 'tecnico' &&
                request.serviceInProgress) ...[
              _MechanicTrackingMapCard(request: request),
              const SizedBox(height: 14),
            ],
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
                            label: 'Monto final',
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
                            label: 'Estado de pago',
                            value: request.paymentReady
                                ? 'Pago QR disponible para el cliente'
                                : 'Esperando que el mecanico vaya en camino o cierre el servicio',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    request.hasAcceptedQuote
                        ? 'El cliente ya acepto una cotizacion. Ese monto queda fijo y no puede modificarse.'
                        : 'Define el monto que debe pagar el cliente. El cliente vera el QR y confirmara el pago desde su cuenta.',
                    style: const TextStyle(
                      color: Color(0xFF6F655B),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      FilledButton.tonalIcon(
                        onPressed: request.hasAcceptedQuote
                            ? null
                            : () =>
                                  _showCostEditor(context, controller, request),
                        icon: Icon(
                          request.hasAcceptedQuote
                              ? Icons.lock_outline
                              : Icons.edit_outlined,
                        ),
                        label: Text(
                          request.hasAcceptedQuote
                              ? 'Monto fijado'
                              : 'Editar monto',
                        ),
                      ),
                      OutlinedButton.icon(
                        onPressed: request.paymentReady
                            ? () => _showGatewayQr(context, request)
                            : null,
                        icon: const Icon(Icons.qr_code_2_outlined),
                        label: const Text('Ver QR de pago'),
                      ),
                    ],
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

  static void _showGatewayQr(BuildContext context, EmergencyRequest request) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('QR de pago - Solicitud #${request.id}'),
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
            Text('Referencia: Solicitud #${request.id}'),
          ],
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

  static void _showCostEditor(
    BuildContext context,
    AppController controller,
    EmergencyRequest request,
  ) {
    showDialog<void>(
      context: context,
      builder: (_) => _CostDialog(controller: controller, request: request),
    );
  }

  static Future<void> _openAudio(
    BuildContext context,
    AppController controller,
    EmergencyRequest request,
  ) async {
    final url = ApiClient(
      baseUrl: controller.baseUrl,
    ).resolveAssetUrl(request.audioUrl);
    if (url == null) {
      return;
    }
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  static Future<void> _openRoute(EmergencyRequest request) async {
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=${request.latitud},${request.longitud}&travelmode=driving',
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}

class _CostDialog extends StatefulWidget {
  const _CostDialog({required this.controller, required this.request});

  final AppController controller;
  final EmergencyRequest request;

  @override
  State<_CostDialog> createState() => _CostDialogState();
}

class _CostDialogState extends State<_CostDialog> {
  late final TextEditingController _amountController;
  String? _errorText;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _amountController = TextEditingController(
      text: widget.request.precioCobrado?.toStringAsFixed(2) ?? '',
    );
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final amount = double.tryParse(_amountController.text.replaceAll(',', '.'));
    if (amount == null || amount <= 0) {
      setState(() => _errorText = 'Ingresa un monto valido.');
      return;
    }
    setState(() {
      _saving = true;
      _errorText = null;
    });
    try {
      await widget.controller.updateRequestCost(widget.request.id, amount);
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _errorText = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _RutaDialogShell(
      icon: Icons.payments_outlined,
      eyebrow: 'COBRO DEL SERVICIO',
      title: 'Monto de la solicitud #${widget.request.id}',
      subtitle:
          'Define el monto final que el cliente vera antes de confirmar el pago.',
      errorText: _errorText,
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _saving ? null : _submit,
          child: Text(_saving ? 'Guardando...' : 'Guardar monto'),
        ),
      ],
      child: _DialogTextField(
        controller: _amountController,
        label: 'Monto a cobrar',
        suffixText: 'Bs',
        icon: Icons.attach_money,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
      ),
    );
  }
}

class _MechanicTrackingMapCard extends StatefulWidget {
  const _MechanicTrackingMapCard({required this.request});

  final EmergencyRequest request;

  @override
  State<_MechanicTrackingMapCard> createState() =>
      _MechanicTrackingMapCardState();
}

class _MechanicTrackingMapCardState extends State<_MechanicTrackingMapCard> {
  final MapController _mapController = MapController();
  StreamSubscription<Position>? _positionSub;
  Position? _lastPosition;
  String? _errorText;
  bool _sending = false;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startLocalTracking());
  }

  @override
  void didUpdateWidget(covariant _MechanicTrackingMapCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.request.id != widget.request.id) {
      _positionSub?.cancel();
      _positionSub = null;
      _lastPosition = null;
      _errorText = null;
      _started = false;
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => _startLocalTracking(),
      );
    }
  }

  @override
  void dispose() {
    _positionSub?.cancel();
    super.dispose();
  }

  Future<void> _startLocalTracking() async {
    if (_started || !mounted) return;
    _started = true;

    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        if (mounted) {
          setState(() {
            _errorText =
                'Activa el permiso de ubicacion para ver tu ruta en vivo.';
          });
        }
        return;
      }

      final current = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
      _setPosition(current);

      _positionSub =
          Geolocator.getPositionStream(
            locationSettings: const LocationSettings(
              accuracy: LocationAccuracy.high,
              distanceFilter: 5,
            ),
          ).listen(
            _setPosition,
            onError: (Object error) {
              if (!mounted) return;
              setState(() {
                _errorText = 'No se pudo actualizar GPS: $error';
              });
            },
          );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorText = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  void _setPosition(Position position) {
    if (!mounted) return;
    setState(() {
      _lastPosition = position;
      _errorText = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final center = _centerFor(position);
      _mapController.move(center, 13);
    });
  }

  LatLng _centerFor(Position position) {
    return LatLng(
      (position.latitude + widget.request.latitud) / 2,
      (position.longitude + widget.request.longitud) / 2,
    );
  }

  Future<void> _shareNow(AppController controller) async {
    setState(() {
      _sending = true;
      _errorText = null;
    });
    try {
      final position = await controller.sendCurrentMechanicLocation(
        widget.request,
      );
      _setPosition(position);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ubicacion enviada al cliente.')),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorText = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final destination = LatLng(widget.request.latitud, widget.request.longitud);
    final mechanic = _lastPosition == null
        ? null
        : LatLng(_lastPosition!.latitude, _lastPosition!.longitude);
    final center = mechanic == null
        ? destination
        : LatLng(
            (mechanic.latitude + destination.latitude) / 2,
            (mechanic.longitude + destination.longitude) / 2,
          );

    return _SectionCard(
      title: 'Ruta al cliente',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: SizedBox(
              height: 260,
              child: FlutterMap(
                mapController: _mapController,
                options: MapOptions(initialCenter: center, initialZoom: 13),
                children: [
                  TileLayer(
                    urlTemplate:
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.rutasos.mobile',
                  ),
                  if (mechanic != null)
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: [mechanic, destination],
                          strokeWidth: 5,
                          color: const Color(0xFF8D5524),
                        ),
                      ],
                    ),
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: destination,
                        width: 46,
                        height: 46,
                        child: const Icon(
                          Icons.location_pin,
                          color: Color(0xFFB3261E),
                          size: 42,
                        ),
                      ),
                      if (mechanic != null)
                        Marker(
                          point: mechanic,
                          width: 46,
                          height: 46,
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.18),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: const Icon(
                              Icons.engineering,
                              color: Color(0xFF2E7D32),
                              size: 30,
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Text(
                  mechanic == null
                      ? 'Esperando GPS del mecanico.'
                      : 'Ubicacion activa. El cliente recibe el movimiento en tiempo real.',
                  style: const TextStyle(
                    color: Color(0xFF6F655B),
                    height: 1.35,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              FilledButton.icon(
                onPressed: _sending ? null : () => _shareNow(controller),
                icon: _sending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.near_me_outlined),
                label: Text(_sending ? 'Enviando' : 'Compartir'),
              ),
            ],
          ),
          if (_errorText != null) ...[
            const SizedBox(height: 10),
            Text(
              _errorText!,
              style: const TextStyle(
                color: Color(0xFFB3261E),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _QuoteDialog extends StatefulWidget {
  const _QuoteDialog({required this.controller, required this.request});

  final AppController controller;
  final EmergencyRequest request;

  @override
  State<_QuoteDialog> createState() => _QuoteDialogState();
}

class _QuoteDialogState extends State<_QuoteDialog> {
  final _amountController = TextEditingController();
  final _etaController = TextEditingController(text: '20');
  final _hoursController = TextEditingController(text: '1');
  final _warrantyController = TextEditingController(text: '7');
  final _descriptionController = TextEditingController();
  bool _includesParts = false;
  bool _sending = false;
  String? _errorText;

  @override
  void dispose() {
    _amountController.dispose();
    _etaController.dispose();
    _hoursController.dispose();
    _warrantyController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final amount = double.tryParse(_amountController.text.replaceAll(',', '.'));
    final eta = int.tryParse(_etaController.text);
    final hours = double.tryParse(_hoursController.text.replaceAll(',', '.'));
    final warranty = int.tryParse(_warrantyController.text) ?? 0;

    if (amount == null ||
        amount <= 0 ||
        eta == null ||
        eta <= 0 ||
        hours == null ||
        hours <= 0) {
      setState(() => _errorText = 'Completa costo, llegada y horas.');
      return;
    }

    setState(() {
      _sending = true;
      _errorText = null;
    });

    try {
      await widget.controller.createCotizacion(
        request: widget.request,
        costoEstimado: amount,
        tiempoReparacionHoras: hours,
        etaLlegadaMinutos: eta,
        descripcion: _descriptionController.text,
        incluyeRepuestos: _includesParts,
        garantiaDias: warranty,
      );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _errorText = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _RutaDialogShell(
      icon: Icons.request_quote_outlined,
      eyebrow: 'COTIZACION AL CLIENTE',
      title: 'Cotizar solicitud #${widget.request.id}',
      subtitle:
          'Envia una propuesta clara. El cliente vera el costo, la llegada estimada y la garantia antes de elegir taller.',
      errorText: _errorText,
      actions: [
        TextButton(
          onPressed: _sending ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton.icon(
          onPressed: _sending ? null : _submit,
          icon: _sending
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.send_outlined),
          label: Text(_sending ? 'Enviando...' : 'Enviar cotizacion'),
        ),
      ],
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Expanded(
                child: _DialogTextField(
                  controller: _amountController,
                  label: 'Costo',
                  suffixText: 'Bs',
                  icon: Icons.payments_outlined,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _DialogTextField(
                  controller: _etaController,
                  label: 'Llegada',
                  suffixText: 'min',
                  icon: Icons.schedule_outlined,
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _DialogTextField(
                  controller: _hoursController,
                  label: 'Reparacion',
                  suffixText: 'h',
                  icon: Icons.build_outlined,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _DialogTextField(
                  controller: _warrantyController,
                  label: 'Garantia',
                  suffixText: 'dias',
                  icon: Icons.verified_outlined,
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _DialogTextField(
            controller: _descriptionController,
            label: 'Detalle para el cliente',
            icon: Icons.notes_outlined,
            minLines: 3,
            maxLines: 4,
            keyboardType: TextInputType.multiline,
          ),
          const SizedBox(height: 12),
          DecoratedBox(
            decoration: BoxDecoration(
              color: const Color(0xFFFFF8EF),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFE8D6C3)),
            ),
            child: SwitchListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 14),
              value: _includesParts,
              activeThumbColor: const Color(0xFF8D5524),
              title: const Text(
                'Incluye repuestos',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: const Text(
                'Activalo si el precio ya contempla piezas o insumos.',
              ),
              onChanged: _sending
                  ? null
                  : (value) => setState(() => _includesParts = value),
            ),
          ),
        ],
      ),
    );
  }
}

class _RutaDialogShell extends StatelessWidget {
  const _RutaDialogShell({
    required this.icon,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
    required this.child,
    required this.actions,
    this.errorText,
  });

  final IconData icon;
  final String eyebrow;
  final String title;
  final String subtitle;
  final Widget child;
  final List<Widget> actions;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 24),
      backgroundColor: Colors.transparent,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: const Color(0xFFFFF8EF),
            borderRadius: BorderRadius.circular(30),
            border: Border.all(color: const Color(0xFFE0C9B4)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.22),
                blurRadius: 34,
                offset: const Offset(0, 18),
              ),
            ],
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    DecoratedBox(
                      decoration: BoxDecoration(
                        color: const Color(0xFF3A2416),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(11),
                        child: Icon(icon, color: Colors.white, size: 22),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            eyebrow,
                            style: const TextStyle(
                              color: Color(0xFF9A5F2B),
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.8,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            title,
                            style: const TextStyle(
                              color: Color(0xFF2B211B),
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: Color(0xFF725E4F),
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 18),
                child,
                if (errorText != null) ...[
                  const SizedBox(height: 12),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFE9E6),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFFFB8AE)),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: Color(0xFFB3261E),
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              errorText!,
                              style: const TextStyle(
                                color: Color(0xFF9A1B16),
                                fontWeight: FontWeight.w700,
                                height: 1.35,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: actions
                      .map(
                        (action) => Padding(
                          padding: const EdgeInsets.only(left: 8),
                          child: action,
                        ),
                      )
                      .toList(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DialogTextField extends StatelessWidget {
  const _DialogTextField({
    required this.controller,
    required this.label,
    required this.icon,
    this.suffixText,
    this.keyboardType,
    this.minLines,
    this.maxLines = 1,
  });

  final TextEditingController controller;
  final String label;
  final IconData icon;
  final String? suffixText;
  final TextInputType? keyboardType;
  final int? minLines;
  final int? maxLines;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      minLines: minLines,
      maxLines: maxLines,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        suffixText: suffixText,
        filled: true,
        fillColor: const Color(0xFFFFFCF7),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFFE1C9B2)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFFE1C9B2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFF8D5524), width: 1.7),
        ),
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
          if (controller.currentUser?.role == 'tecnico' &&
              request.serviceInProgress) ...[
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => _sendLocation(context, controller),
              icon: const Icon(Icons.my_location_outlined),
              label: const Text('Compartir ubicacion actual'),
            ),
            const SizedBox(height: 10),
          ],
          if (request.tallerId == null &&
              controller.canWorkshopTakeRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => _showQuoteEditor(context, controller),
              icon: const Icon(Icons.request_quote_outlined),
              label: const Text('Enviar cotizacion al cliente'),
            ),
          if (request.tallerId == null &&
              controller.canWorkshopTakeRequest(request)) ...[
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => _pickTechnicianAndAssign(context, controller),
              icon: const Icon(Icons.engineering_outlined),
              label: const Text('Tomar servicio y asignar tecnico'),
            ),
          ],
          if (request.estado == 'asignada' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'tecnico_en_camino',
                    ),
              icon: const Icon(Icons.route_outlined),
              label: const Text('Marcar tecnico en camino'),
            ),
          if (request.estado == 'tecnico_en_camino' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'tecnico_llego',
                    ),
              icon: const Icon(Icons.location_on_outlined),
              label: const Text('Marcar llegada al incidente'),
            ),
          if (request.estado == 'tecnico_llego' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'en_proceso',
                    ),
              icon: const Icon(Icons.build_circle_outlined),
              label: const Text('Iniciar atencion'),
            ),
          if (request.estado == 'en_proceso' &&
              controller.canWorkshopManageRequest(request))
            FilledButton.icon(
              onPressed: controller.loading
                  ? null
                  : () => controller.advanceRequestStatus(
                      request: request,
                      estado: 'finalizado',
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
                  : () => _confirmCancelRequest(context, controller),
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

  Future<void> _showQuoteEditor(
    BuildContext context,
    AppController controller,
  ) async {
    final submitted = await showDialog<bool>(
      context: context,
      builder: (_) => _QuoteDialog(controller: controller, request: request),
    );

    if (submitted == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cotizacion enviada al cliente.')),
      );
    }
  }

  Future<void> _sendLocation(
    BuildContext context,
    AppController controller,
  ) async {
    try {
      await controller.sendCurrentMechanicLocation(request);
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ubicacion enviada al cliente.')),
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

  Future<void> _confirmCancelRequest(
    BuildContext context,
    AppController controller,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Cancelar solicitud'),
        content: const Text(
          'Se notificara al conductor que el taller cancelo la atencion de esta solicitud.',
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
