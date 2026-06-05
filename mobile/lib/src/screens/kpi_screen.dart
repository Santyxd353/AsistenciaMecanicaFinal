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
  KpiBundle? _data;
  String? _error;
  bool _loading = true;

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
      final data = await svc.fetchAll();
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'No se pudieron cargar los KPIs: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analítica operacional'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Text(_error!)))
              : _data == null
                  ? const Center(child: Text('Sin datos.'))
                  : _buildBody(_data!),
    );
  }

  Widget _buildBody(KpiBundle d) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _grid([
            _metric('Tiempo asignación', _mins(d.assignmentAvgMin)),
            _metric('Tiempo llegada', _mins(d.arrivalAvgMin)),
            _metric('Cumplimiento SLA', d.slaPercentage == null ? '—' : '${d.slaPercentage!.toStringAsFixed(1)}%'),
            _metric('Cancelados', '${d.canceladosCount}'),
          ]),
          const SizedBox(height: 16),
          _section('Incidentes por tipo'),
          ...d.incidentesPorTipo.entries.map((e) => _bar(e.key, e.value, _maxIncidentes(d))),
          const SizedBox(height: 16),
          _section('Talleres más eficientes'),
          if (d.topTalleres.isEmpty) const _Empty('Aún no hay datos suficientes.'),
          ...d.topTalleres.map((t) => ListTile(
                leading: const Icon(Icons.build),
                title: Text(t.nombre),
                subtitle: Text('${t.servicios} servicio(s)'),
                trailing: Text('${(t.score * 100).toStringAsFixed(0)}%'),
              )),
          const SizedBox(height: 16),
          _section('Zonas con más incidentes'),
          if (d.zonas.isEmpty) const _Empty('Aún no hay datos geográficos.'),
          ...d.zonas.map((z) => ListTile(
                leading: const Icon(Icons.location_on),
                title: Text('${z.lat.toStringAsFixed(3)}, ${z.lng.toStringAsFixed(3)}'),
                trailing: Text('${z.count}'),
              )),
        ],
      ),
    );
  }

  String _mins(double? v) => v == null ? '—' : '${v.toStringAsFixed(1)} min';

  int _maxIncidentes(KpiBundle d) =>
      d.incidentesPorTipo.values.fold<int>(0, (a, b) => b > a ? b : a);

  Widget _grid(List<Widget> children) => GridView.count(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        childAspectRatio: 1.6,
        children: children,
      );

  Widget _metric(String label, String value) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFFDF6EC),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFEADCCA)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.4, color: Color(0xFF8A6647))),
            const SizedBox(height: 6),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1F1A16))),
          ],
        ),
      );

  Widget _section(String title) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      );

  Widget _bar(String label, int count, int max) {
    final ratio = max == 0 ? 0.0 : (count / max).clamp(0.0, 1.0);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(label),
            Text('$count'),
          ]),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 8,
              backgroundColor: const Color(0xFFF4DBB9),
              color: const Color(0xFFB5651D),
            ),
          ),
        ],
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;
  @override
  Widget build(BuildContext c) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Text(text, style: const TextStyle(fontStyle: FontStyle.italic, color: Colors.grey)),
      );
}
