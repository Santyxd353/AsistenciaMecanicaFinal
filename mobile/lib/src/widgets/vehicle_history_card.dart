import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class VehicleHistoryCard extends StatefulWidget {
  const VehicleHistoryCard({
    super.key,
    required this.vehicleId,
    this.title = 'Historial del vehiculo',
  });

  final int vehicleId;
  final String title;

  @override
  State<VehicleHistoryCard> createState() => _VehicleHistoryCardState();
}

class _VehicleHistoryCardState extends State<VehicleHistoryCard> {
  late Future<List<VehicleRepairHistory>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void didUpdateWidget(covariant VehicleHistoryCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.vehicleId != widget.vehicleId) {
      _future = _load();
    }
  }

  Future<List<VehicleRepairHistory>> _load() {
    return context.read<AppController>().fetchVehicleHistory(widget.vehicleId);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.car_repair_outlined, color: Color(0xFF8D5524)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    widget.title,
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 16,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Actualizar historial',
                  onPressed: () => setState(() => _future = _load()),
                  icon: const Icon(Icons.sync),
                ),
              ],
            ),
            const SizedBox(height: 12),
            FutureBuilder<List<VehicleRepairHistory>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: LinearProgressIndicator(),
                  );
                }
                if (snapshot.hasError) {
                  return Text(
                    snapshot.error.toString().replaceFirst('Exception: ', ''),
                    style: const TextStyle(
                      color: Color(0xFFB13C31),
                      fontWeight: FontWeight.w700,
                    ),
                  );
                }
                final items = snapshot.data ?? const [];
                if (items.isEmpty) {
                  return const Text(
                    'Este vehiculo todavia no tiene reparaciones registradas.',
                    style: TextStyle(color: Color(0xFF6F655B)),
                  );
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _HistorySummary(items: items),
                    const SizedBox(height: 12),
                    ..._recurrentAlerts(items).map(
                      (alert) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: const Color(0xFFFFF1D8),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFFE0B980)),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.warning_amber_rounded,
                                  color: Color(0xFF8D5524),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    alert,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w800,
                                      color: Color(0xFF5C3418),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    ...items.map((item) => _HistoryTile(item: item)),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _HistorySummary extends StatelessWidget {
  const _HistorySummary({required this.items});

  final List<VehicleRepairHistory> items;

  @override
  Widget build(BuildContext context) {
    final total = items.fold<double>(0, (sum, item) => sum + (item.cost ?? 0));
    final lastDate = DateFormat(
      'dd/MM/yyyy',
    ).format(items.first.serviceDate.toLocal());

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _SummaryPill(label: 'Reparaciones', value: '${items.length}'),
          _SummaryPill(label: 'Ultima atencion', value: lastDate),
          _SummaryPill(
            label: 'Costo acumulado',
            value: 'Bs ${total.toStringAsFixed(2)}',
          ),
        ],
      ),
    );
  }
}

class _SummaryPill extends StatelessWidget {
  const _SummaryPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 130),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF8A6647),
              fontSize: 10,
              fontWeight: FontWeight.w900,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
        ],
      ),
    );
  }
}

List<String> _recurrentAlerts(List<VehicleRepairHistory> items) {
  final counts = <String, int>{};
  for (final item in items) {
    final key = (item.category ?? '').trim().toLowerCase();
    if (key.isEmpty) continue;
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts.entries
      .where((entry) => entry.value >= 2)
      .map(
        (entry) =>
            'Falla recurrente detectada: ${entry.key} (${entry.value} registros).',
      )
      .toList(growable: false);
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.item});

  final VehicleRepairHistory item;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('dd/MM/yyyy - HH:mm');
    final detail = (item.diagnosis?.trim().isNotEmpty ?? false)
        ? item.diagnosis!.trim()
        : ((item.actions?.trim().isNotEmpty ?? false)
              ? item.actions!.trim()
              : 'Sin detalle tecnico.');

    return Container(
      width: double.infinity,
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ),
              Text(
                formatter.format(item.serviceDate.toLocal()),
                style: const TextStyle(color: Color(0xFF8A6647), fontSize: 11),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(detail, style: const TextStyle(height: 1.35)),
          if ((item.actions ?? '').trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              item.actions!.trim(),
              style: const TextStyle(
                height: 1.35,
                color: Color(0xFF6F655B),
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if ((item.category ?? '').trim().isNotEmpty)
                Chip(label: Text(item.category!.trim())),
              if ((item.priority ?? '').trim().isNotEmpty)
                Chip(label: Text(item.priority!.trim())),
              if (item.mileage != null) Chip(label: Text('${item.mileage} km')),
              if ((item.workshopName ?? '').trim().isNotEmpty)
                Chip(label: Text(item.workshopName!.trim())),
              if ((item.technicianName ?? '').trim().isNotEmpty)
                Chip(label: Text(item.technicianName!.trim())),
              if (item.cost != null)
                Chip(label: Text('Bs ${item.cost!.toStringAsFixed(2)}')),
              if ((item.paymentStatus ?? '').trim().isNotEmpty)
                Chip(label: Text(item.paymentStatus!.trim())),
            ],
          ),
        ],
      ),
    );
  }
}
