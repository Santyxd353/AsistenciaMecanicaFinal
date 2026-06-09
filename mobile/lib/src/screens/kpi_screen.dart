import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../services/kpi_service.dart';

class KpiScreen extends StatefulWidget {
  const KpiScreen({super.key});

  @override
  State<KpiScreen> createState() => _KpiScreenState();
}

class _KpiScreenState extends State<KpiScreen> {
  WorkshopReportsBundle? _data;
  String? _error;
  bool _loading = true;
  int _days = 30;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final ctrl = context.read<AppController>();
      final svc = KpiService(() => ctrl.apiClient);
      final data = await svc.fetchWorkshopReports(days: _days);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'No se pudieron cargar los reportes: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F0E6),
      appBar: AppBar(
        backgroundColor: const Color(0xFFF7F0E6),
        elevation: 0,
        title: const Text('Reportes del taller'),
        actions: [
          PopupMenuButton<int>(
            initialValue: _days,
            onSelected: (value) {
              setState(() => _days = value);
              _load();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 7, child: Text('Ultimos 7 dias')),
              PopupMenuItem(value: 30, child: Text('Ultimos 30 dias')),
              PopupMenuItem(value: 90, child: Text('Ultimos 90 dias')),
            ],
            icon: const Icon(Icons.date_range),
          ),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorState(message: _error!, onRetry: _load)
              : _data == null
                  ? const Center(child: Text('Sin datos.'))
                  : _ReportsBody(data: _data!, onRefresh: _load),
    );
  }
}

class _ReportsBody extends StatelessWidget {
  const _ReportsBody({required this.data, required this.onRefresh});

  final WorkshopReportsBundle data;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final s = data.resumen;
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(18, 10, 18, 110),
        children: [
          Text(
            data.tallerNombre,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.8,
              color: Color(0xFF9A6337),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Vista de los ultimos ${data.ventanaDias} dias',
            style: const TextStyle(color: Color(0xFF765D4A)),
          ),
          const SizedBox(height: 18),
          _SummaryGrid(summary: s),
          const SizedBox(height: 18),
          _SectionCard(
            title: 'Trabajadores con mas rendimiento',
            subtitle: 'Servicios cerrados, tiempo, calificacion e ingresos.',
            child: data.trabajadores.isEmpty
                ? const _EmptyLine('Aun no hay trabajos asignados a mecanicos.')
                : Column(
                    children: [
                      for (var i = 0; i < data.trabajadores.length; i++)
                        _WorkerTile(item: data.trabajadores[i], rank: i + 1),
                    ],
                  ),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Tipos de incidentes mas frecuentes',
            subtitle: 'Fallas que mas se repiten en tu taller.',
            child: _Bars(items: data.tiposIncidente),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Modelos de auto mas auxiliados',
            subtitle: 'Vehiculos que aparecen con mayor frecuencia.',
            child: _Bars(items: data.modelosAuxiliados),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Marcas mas atendidas',
            subtitle: 'Resumen por marca registrada.',
            child: _Bars(items: data.marcasAuxiliadas),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Zonas con mas auxilio',
            subtitle: 'Puntos aproximados donde mas pidieron ayuda.',
            child: data.zonas.isEmpty
                ? const _EmptyLine('Aun no hay datos de ubicacion.')
                : Column(
                    children: data.zonas
                        .map(
                          (z) => ListTile(
                            dense: true,
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(
                              Icons.location_on,
                              color: Color(0xFF9A6337),
                            ),
                            title: Text(
                              '${z.lat.toStringAsFixed(3)}, ${z.lng.toStringAsFixed(3)}',
                              style: const TextStyle(fontWeight: FontWeight.w800),
                            ),
                            trailing: _Pill('${z.total} casos'),
                          ),
                        )
                        .toList(),
                  ),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Estados de solicitudes',
            subtitle: 'Como se esta moviendo la bandeja del taller.',
            child: _Bars(items: data.estados),
          ),
        ],
      ),
    );
  }
}

class _SummaryGrid extends StatelessWidget {
  const _SummaryGrid({required this.summary});

  final WorkshopReportSummary summary;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.45,
      children: [
        _MetricCard('Solicitudes', '${summary.solicitudes}', 'Total recibido'),
        _MetricCard('Activas', '${summary.activas}', 'En atencion'),
        _MetricCard('Finalizadas', '${summary.finalizadas}', 'Servicios cerrados'),
        _MetricCard('Canceladas', '${summary.canceladas}', 'Casos perdidos'),
        _MetricCard('Ingresos', _money(summary.ingresos), 'Monto bruto'),
        _MetricCard('Neto taller', _money(summary.neto), 'Sin comision'),
        _MetricCard('Llegada prom.', _mins(summary.tiempoLlegadaMin), 'Hasta cliente'),
        _MetricCard('Cierre prom.', _mins(summary.tiempoCierreMin), 'Caso completo'),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard(this.label, this.value, this.caption);

  final String label;
  final String value;
  final String caption;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFEAD7C3)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 18,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.3,
              color: Color(0xFF9A6337),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w900,
              color: Color(0xFF2D1A0F),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            caption,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Color(0xFF7A6654), fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFFEAD7C3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: Color(0xFF2D1A0F),
            ),
          ),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: Color(0xFF765D4A))),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _WorkerTile extends StatelessWidget {
  const _WorkerTile({required this.item, required this.rank});

  final WorkerReportItem item;
  final int rank;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFCF6EE),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFEAD7C3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: const Color(0xFF3A2112),
            foregroundColor: Colors.white,
            child: Text('$rank'),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.nombre,
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _Pill('${item.finalizados} cerrados'),
                    _Pill('${item.tasaFinalizacion.toStringAsFixed(0)}% cierre'),
                    _Pill('${item.calificacion.toStringAsFixed(1)} estrellas'),
                    _Pill(_money(item.ingresos)),
                  ],
                ),
                if (item.tiempoCierreMin != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Tiempo promedio: ${_mins(item.tiempoCierreMin)}',
                    style: const TextStyle(color: Color(0xFF765D4A)),
                  ),
                ],
              ],
            ),
          ),
          Text(
            item.score.toStringAsFixed(0),
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w900,
              color: Color(0xFF9A6337),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bars extends StatelessWidget {
  const _Bars({required this.items});

  final List<ReportCountItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const _EmptyLine('Aun no hay datos suficientes.');
    }
    final max = items.fold<int>(0, (value, item) => item.total > value ? item.total : value);
    return Column(
      children: items.map((item) {
        final ratio = max == 0 ? 0.0 : (item.total / max).clamp(0.0, 1.0);
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 7),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      item.nombre,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text('${item.total}'),
                ],
              ),
              const SizedBox(height: 5),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(
                  value: ratio,
                  minHeight: 9,
                  backgroundColor: const Color(0xFFEBD8C3),
                  color: const Color(0xFFA16232),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF1E2D2),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w800,
          color: Color(0xFF5A321C),
        ),
      ),
    );
  }
}

class _EmptyLine extends StatelessWidget {
  const _EmptyLine(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Text(
        text,
        style: const TextStyle(color: Color(0xFF806A58)),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.warning_amber_rounded, size: 48, color: Color(0xFFA16232)),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton(onPressed: onRetry, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }
}

String _money(double value) => 'Bs ${value.toStringAsFixed(0)}';

String _mins(double? value) => value == null ? '-' : '${value.toStringAsFixed(0)} min';
