import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';

import '../app_controller.dart';
import '../models.dart';
import 'request_detail_screen.dart';

class OverviewScreen extends StatefulWidget {
  const OverviewScreen({
    super.key,
    required this.onCreateReport,
    required this.onRegisterVehicle,
  });

  final VoidCallback onCreateReport;
  final VoidCallback onRegisterVehicle;

  @override
  State<OverviewScreen> createState() => _OverviewScreenState();
}

class _OverviewScreenState extends State<OverviewScreen> {
  final _voiceSearchController = TextEditingController();
  final _audioRecorder = AudioRecorder();
  final _searchResultPlayer = AudioPlayer();

  bool _showHistorySearch = false;
  bool _recordingVoiceSearch = false;
  bool _transcribingVoiceSearch = false;
  bool _playingSearchSummary = false;
  DateTimeRange? _dateRange;
  String? _incidentFilter;

  @override
  void dispose() {
    _voiceSearchController.dispose();
    _audioRecorder.dispose();
    _searchResultPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final requests = controller.requests;
    final visibleRequests = _visibleRequests(requests);
    final incidentOptions = _incidentOptions(requests);
    final searchSummary = _searchSummary(visibleRequests);
    final notifications = controller.notifications.take(4).toList();
    final activeCount = controller.activeRequests.length;
    final closedCount = requests.length - activeCount;

    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: controller.refreshData,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
            children: [
              _HeroCard(
                user: controller.currentUser,
                vehicleCount: controller.vehicles.length,
                activeCount: activeCount,
                onCreateReport: widget.onCreateReport,
                onRegisterVehicle: widget.onRegisterVehicle,
              ),
              const SizedBox(height: 16),
              if (controller.currentUser == null || controller.vehicles.isEmpty)
                _SetupWarning(
                  missingProfile: controller.currentUser == null,
                  missingVehicles: controller.vehicles.isEmpty,
                  onRegisterVehicle: widget.onRegisterVehicle,
                ),
              if (controller.currentUser == null || controller.vehicles.isEmpty)
                const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _MetricCard(
                      title: 'Seguimiento',
                      value: requests.length.toString(),
                      caption: 'Solicitudes creadas',
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
                _showHistorySearch ? 'Buscar solicitudes' : 'Ultima solicitud',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: controller.loading
                    ? null
                    : () => setState(
                        () => _showHistorySearch = !_showHistorySearch,
                      ),
                icon: Icon(
                  _showHistorySearch
                      ? Icons.expand_less
                      : Icons.manage_search_outlined,
                ),
                label: Text(
                  _showHistorySearch
                      ? 'Ocultar buscador'
                      : 'Buscar historial',
                ),
              ),
              if (_showHistorySearch) ...[
                const SizedBox(height: 10),
                _HistorySearchCard(
                  dateRange: _dateRange,
                  incidentFilter: _incidentFilter,
                  incidentOptions: incidentOptions,
                  voiceSearchController: _voiceSearchController,
                  recordingVoiceSearch: _recordingVoiceSearch,
                  transcribingVoiceSearch: _transcribingVoiceSearch,
                  onPickDateRange: _pickDateRange,
                  onIncidentChanged: (value) =>
                      setState(() => _incidentFilter = value),
                  onVoiceSearch: () => _toggleVoiceSearch(controller),
                  onTextChanged: (_) => setState(() {}),
                  onClear: _clearSearch,
                ),
                const SizedBox(height: 10),
                _SearchResultSummary(
                  total: visibleRequests.length,
                  incidentLabel: searchSummary,
                  playing: _playingSearchSummary,
                  onPlay: () => _playSearchResultAudio(
                    controller: controller,
                    total: visibleRequests.length,
                    incidentLabel: searchSummary,
                  ),
                ),
              ],
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
                          onPressed: widget.onCreateReport,
                          icon: const Icon(Icons.add_location_alt_outlined),
                          label: const Text('Crear primer reporte'),
                        ),
                      ],
                    ),
                  ),
                )
              else if (visibleRequests.isEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'No encontramos solicitudes con esos filtros.',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Prueba con otro rango de fechas, tipo de incidencia o busqueda por voz.',
                        ),
                      ],
                    ),
                  ),
                )
              else
                ...visibleRequests.map(
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
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
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
      ),
    );
  }

  List<EmergencyRequest> _visibleRequests(List<EmergencyRequest> requests) {
    final sorted = requests.toList()
      ..sort((left, right) => right.fechaCreacion.compareTo(left.fechaCreacion));
    if (!_showHistorySearch) {
      return sorted.take(1).toList();
    }

    final query = _normalize(_voiceSearchController.text);
    return sorted.where((request) {
      final createdAt = request.fechaCreacion.toLocal();
      final range = _dateRange;
      if (range != null) {
        final start = DateTime(
          range.start.year,
          range.start.month,
          range.start.day,
        );
        final end = DateTime(
          range.end.year,
          range.end.month,
          range.end.day,
          23,
          59,
          59,
          999,
        );
        if (createdAt.isBefore(start) || createdAt.isAfter(end)) {
          return false;
        }
      }

      final incident = _incidentLabel(request);
      if (_incidentFilter != null && incident != _incidentFilter) {
        return false;
      }

      if (query.isEmpty) {
        return true;
      }
      final searchable = _normalize(
        [
          request.descripcion,
          request.clasificacionIa,
          request.resumenIa,
          request.especialidadRequeridaIa,
          request.tallerNombre,
          request.tecnicoNombre,
          request.vehiculoPlaca,
          request.vehiculoDescripcion,
        ].whereType<String>().join(' '),
      );
      return searchable.contains(query);
    }).toList();
  }

  List<String> _incidentOptions(List<EmergencyRequest> requests) {
    final byNormalized = <String, String>{};
    for (final request in requests) {
      final label = _incidentLabel(request).trim();
      if (label.isEmpty) {
        continue;
      }
      byNormalized.putIfAbsent(_normalize(label), () => label);
    }
    return byNormalized.values.toList()..sort();
  }

  String _incidentLabel(EmergencyRequest request) {
    final specialty = request.especialidadRequeridaIa?.trim();
    if (specialty != null && specialty.isNotEmpty) {
      return specialty;
    }
    final classification = request.clasificacionIa?.trim();
    if (classification != null && classification.isNotEmpty) {
      return classification;
    }
    return 'Sin clasificar';
  }

  String _normalize(String value) {
    return value
        .toLowerCase()
        .replaceAll('á', 'a')
        .replaceAll('é', 'e')
        .replaceAll('í', 'i')
        .replaceAll('ó', 'o')
        .replaceAll('ú', 'u')
        .replaceAll('ü', 'u')
        .replaceAll('ñ', 'n')
        .trim();
  }

  String _searchSummary(List<EmergencyRequest> requests) {
    if (_incidentFilter != null && _incidentFilter!.trim().isNotEmpty) {
      return _incidentFilter!.trim();
    }
    final query = _voiceSearchController.text.trim();
    if (query.isNotEmpty) {
      return query;
    }
    if (requests.isEmpty) {
      return 'los filtros indicados';
    }
    final grouped = <String, int>{};
    for (final request in requests) {
      final label = _incidentLabel(request);
      grouped[label] = (grouped[label] ?? 0) + 1;
    }
    final entries = grouped.entries.toList()
      ..sort((left, right) => right.value.compareTo(left.value));
    return entries.first.key;
  }

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year - 3),
      lastDate: DateTime(now.year + 1),
      initialDateRange:
          _dateRange ??
          DateTimeRange(
            start: now.subtract(const Duration(days: 30)),
            end: now,
          ),
    );
    if (picked != null && mounted) {
      setState(() => _dateRange = picked);
    }
  }

  Future<void> _toggleVoiceSearch(AppController controller) async {
    if (_recordingVoiceSearch) {
      final path = await _audioRecorder.stop();
      if (!mounted) {
        return;
      }
      setState(() {
        _recordingVoiceSearch = false;
        _transcribingVoiceSearch = path != null && path.isNotEmpty;
      });
      if (path == null || path.isEmpty) {
        return;
      }
      try {
        final text = await controller.transcribeEmergencyAudio(path);
        if (!mounted) {
          return;
        }
        _applyConversationalSearch(text, controller.requests);
        setState(() => _transcribingVoiceSearch = false);
        final filtered = _visibleRequests(controller.requests);
        await _playSearchResultAudio(
          controller: controller,
          total: filtered.length,
          incidentLabel: _searchSummary(filtered),
        );
      } catch (error) {
        if (!mounted) {
          return;
        }
        setState(() => _transcribingVoiceSearch = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
      return;
    }

    final hasPermission = await _audioRecorder.hasPermission();
    if (!hasPermission) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Concede permiso de microfono para buscar por voz.'),
        ),
      );
      return;
    }

    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/busqueda-${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _audioRecorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc),
      path: path,
    );
    if (mounted) {
      setState(() => _recordingVoiceSearch = true);
    }
  }

  void _clearSearch() {
    _voiceSearchController.clear();
    setState(() {
      _dateRange = null;
      _incidentFilter = null;
    });
  }

  void _applyConversationalSearch(
    String spokenText,
    List<EmergencyRequest> requests,
  ) {
    final normalized = _normalize(spokenText);
    final dateRange = _dateRangeFromCommand(normalized);
    final incident = _incidentFromCommand(normalized, requests);
    setState(() {
      if (dateRange != null) {
        _dateRange = dateRange;
      }
      if (incident != null) {
        _incidentFilter = incident;
        _voiceSearchController.text = incident;
      } else {
        _voiceSearchController.text = _cleanSearchCommand(spokenText);
      }
    });
  }

  DateTimeRange? _dateRangeFromCommand(String normalizedText) {
    final now = DateTime.now();
    DateTime dayStart(DateTime value) =>
        DateTime(value.year, value.month, value.day);
    DateTime dayEnd(DateTime value) =>
        DateTime(value.year, value.month, value.day, 23, 59, 59, 999);

    if (normalizedText.contains('ayer')) {
      final yesterday = now.subtract(const Duration(days: 1));
      return DateTimeRange(start: dayStart(yesterday), end: dayEnd(yesterday));
    }
    if (normalizedText.contains('hoy')) {
      return DateTimeRange(start: dayStart(now), end: dayEnd(now));
    }
    if (normalizedText.contains('esta semana')) {
      final start = dayStart(now.subtract(Duration(days: now.weekday - 1)));
      return DateTimeRange(start: start, end: dayEnd(now));
    }
    if (normalizedText.contains('este mes')) {
      final start = DateTime(now.year, now.month);
      return DateTimeRange(start: start, end: dayEnd(now));
    }
    if (normalizedText.contains('ultimos 7 dias') ||
        normalizedText.contains('ultima semana')) {
      return DateTimeRange(
        start: dayStart(now.subtract(const Duration(days: 7))),
        end: dayEnd(now),
      );
    }
    if (normalizedText.contains('ultimos 30 dias') ||
        normalizedText.contains('ultimo mes')) {
      return DateTimeRange(
        start: dayStart(now.subtract(const Duration(days: 30))),
        end: dayEnd(now),
      );
    }
    return null;
  }

  String? _incidentFromCommand(
    String normalizedText,
    List<EmergencyRequest> requests,
  ) {
    final options = _incidentOptions(requests);
    final aliases = <String, List<String>>{
      'bateria': ['bateria', 'baterias', 'electrico', 'electricidad'],
      'frenos': ['freno', 'frenos', 'pedal duro', 'no frena'],
      'motor': ['motor', 'recalienta', 'recalentamiento', 'humo'],
      'llantas': ['llanta', 'llantas', 'goma', 'pinchazo', 'neumatico'],
      'choque': ['choque', 'chocado', 'colision', 'carroceria'],
      'auxilio general': ['auxilio general', 'general'],
    };

    for (final option in options) {
      final normalizedOption = _normalize(option);
      if (normalizedText.contains(normalizedOption)) {
        return option;
      }
      for (final entry in aliases.entries) {
        if (normalizedOption.contains(entry.key) &&
            entry.value.any(normalizedText.contains)) {
          return option;
        }
      }
    }
    for (final entry in aliases.entries) {
      if (entry.value.any(normalizedText.contains)) {
        final matchedOption = options.cast<String?>().firstWhere(
          (option) => _normalize(option ?? '').contains(entry.key),
          orElse: () => null,
        );
        return matchedOption;
      }
    }
    return null;
  }

  String _cleanSearchCommand(String spokenText) {
    var cleaned = _normalize(spokenText);
    const removable = [
      'buscame',
      'buscar',
      'busca',
      'solicitudes',
      'solicitud',
      'incidencias',
      'incidencia',
      'emergencias',
      'emergencia',
      'sobre',
      'de',
      'del',
      'con',
      'por',
      'ayer',
      'hoy',
      'esta semana',
      'este mes',
      'ultimos 7 dias',
      'ultimos 30 dias',
    ];
    for (final word in removable) {
      cleaned = cleaned.replaceAll(word, ' ');
    }
    return cleaned.split(RegExp(r'\s+')).where((word) => word.isNotEmpty).join(' ');
  }

  Future<void> _playSearchResultAudio({
    required AppController controller,
    required int total,
    required String incidentLabel,
  }) async {
    if (_playingSearchSummary) {
      return;
    }
    setState(() => _playingSearchSummary = true);
    try {
      final url = await controller.synthesizeAssistantVoice(
        messageKey: 'search_results',
        especialidad: incidentLabel,
        descripcion: _searchDateLabel(),
        cantidad: total,
      );
      if (url == null || url.isEmpty) {
        return;
      }
      await _searchResultPlayer.stop();
      await _searchResultPlayer.play(UrlSource(url));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _playingSearchSummary = false);
      }
    }
  }

  String? _searchDateLabel() {
    final range = _dateRange;
    if (range == null) {
      return null;
    }
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = DateTime(range.start.year, range.start.month, range.start.day);
    final end = DateTime(range.end.year, range.end.month, range.end.day);
    if (start == today && end == today) {
      return 'hoy';
    }
    if (start == today.subtract(const Duration(days: 1)) &&
        end == today.subtract(const Duration(days: 1))) {
      return 'ayer';
    }
    if (start == DateTime(now.year, now.month)) {
      return 'este mes';
    }
    return null;
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
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFD2C4BB)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14715A3E),
            blurRadius: 22,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              user?.displayName ?? 'Conductor invitado',
              style: const TextStyle(
                color: Color(0xFF322214),
                fontSize: 28,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              activeCount == 0
                  ? 'Listo para reportar una nueva emergencia.'
                  : 'Tienes $activeCount atencion(es) en seguimiento dentro del sistema.',
              style: const TextStyle(color: Color(0xFF4E453E), height: 1.4),
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
                backgroundColor: const Color(0xFF322214),
                foregroundColor: Colors.white,
                shape: const StadiumBorder(),
              ),
              onPressed: onCreateReport,
              icon: const Icon(Icons.sos),
              label: const Text('Reportar emergencia'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF322214),
                side: const BorderSide(color: Color(0xFF322214)),
                shape: const StadiumBorder(),
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
        color: const Color(0xFFF9F3EA),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFD2C4BB)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: const Color(0xFF715A3E)),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(color: Color(0xFF4E453E))),
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

class _HistorySearchCard extends StatelessWidget {
  const _HistorySearchCard({
    required this.dateRange,
    required this.incidentFilter,
    required this.incidentOptions,
    required this.voiceSearchController,
    required this.recordingVoiceSearch,
    required this.transcribingVoiceSearch,
    required this.onPickDateRange,
    required this.onIncidentChanged,
    required this.onVoiceSearch,
    required this.onTextChanged,
    required this.onClear,
  });

  final DateTimeRange? dateRange;
  final String? incidentFilter;
  final List<String> incidentOptions;
  final TextEditingController voiceSearchController;
  final bool recordingVoiceSearch;
  final bool transcribingVoiceSearch;
  final VoidCallback onPickDateRange;
  final ValueChanged<String?> onIncidentChanged;
  final VoidCallback onVoiceSearch;
  final ValueChanged<String> onTextChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('dd/MM/yyyy');
    final rangeLabel = dateRange == null
        ? 'Seleccionar rango de fechas'
        : '${formatter.format(dateRange!.start)} - ${formatter.format(dateRange!.end)}';
    final uniqueIncidentOptions = {
      for (final option in incidentOptions) option,
    }.toList();
    final safeIncidentFilter = uniqueIncidentOptions.contains(incidentFilter)
        ? incidentFilter
        : null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Buscar en historial',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onPickDateRange,
              icon: const Icon(Icons.date_range_outlined),
              label: Text(rangeLabel),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: safeIncidentFilter,
              decoration: const InputDecoration(
                labelText: 'Tipo de incidencia',
              ),
              items: [
                const DropdownMenuItem<String>(
                  value: null,
                  child: Text('Todas las incidencias'),
                ),
                ...uniqueIncidentOptions.map(
                  (item) => DropdownMenuItem<String>(
                    value: item,
                    child: Text(item),
                  ),
                ),
              ],
              onChanged: onIncidentChanged,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: voiceSearchController,
              onChanged: onTextChanged,
              decoration: InputDecoration(
                labelText: 'Buscar por voz o texto',
                hintText: 'Ejemplo: frenos, bateria, motor...',
                suffixIcon: transcribingVoiceSearch
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    : IconButton(
                        onPressed: onVoiceSearch,
                        icon: Icon(
                          recordingVoiceSearch
                              ? Icons.stop_circle_outlined
                              : Icons.mic_none_outlined,
                        ),
                        tooltip: recordingVoiceSearch
                            ? 'Detener busqueda por voz'
                            : 'Buscar por voz',
                      ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: onClear,
                  icon: const Icon(Icons.clear_all_outlined),
                  label: const Text('Limpiar filtros'),
                ),
                if (recordingVoiceSearch)
                  const _MiniMetaChip(
                    icon: Icons.mic,
                    label: 'Grabando busqueda...',
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SearchResultSummary extends StatelessWidget {
  const _SearchResultSummary({
    required this.total,
    required this.incidentLabel,
    required this.playing,
    required this.onPlay,
  });

  final int total;
  final String incidentLabel;
  final bool playing;
  final VoidCallback onPlay;

  @override
  Widget build(BuildContext context) {
    final message = total == 1
        ? 'Se encontro 1 solicitud con incidencia de $incidentLabel.'
        : 'Se encontraron $total solicitudes con incidencias de $incidentLabel.';

    return Card(
      color: const Color(0xFFFFF8EC),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.search_outlined, color: Color(0xFF715A3E)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: Color(0xFF4E453E),
                  fontWeight: FontWeight.w700,
                  height: 1.35,
                ),
              ),
            ),
            IconButton(
              onPressed: playing ? null : onPlay,
              icon: playing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.volume_up_outlined),
              tooltip: 'Escuchar resultado',
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
                  _MiniMetaChip(icon: Icons.av_timer_outlined, label: etaLabel),
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
  const _MiniMetaChip({required this.icon, required this.label});

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
                const Icon(
                  Icons.notifications_active_outlined,
                  color: Color(0xFFC65A16),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    notification.title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text(
                  formatter.format(notification.createdAt.toLocal()),
                  style: const TextStyle(
                    color: Color(0xFF6F655B),
                    fontSize: 12,
                  ),
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
