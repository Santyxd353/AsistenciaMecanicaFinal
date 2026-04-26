import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import 'workshop_request_detail_screen.dart';

class WorkshopRequestsScreen extends StatefulWidget {
  const WorkshopRequestsScreen({super.key});

  @override
  State<WorkshopRequestsScreen> createState() => _WorkshopRequestsScreenState();
}

class _WorkshopRequestsScreenState extends State<WorkshopRequestsScreen> {
  int _selectedFilter = 0;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final requests = switch (_selectedFilter) {
      0 => controller.workshopInboxRequests,
      1 =>
        controller.workshopManagedRequests
            .where((request) => !request.isClosed)
            .toList(),
      _ => controller.workshopClosedRequests,
    };

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: controller.refreshData,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          children: [
            const Text(
              'Servicios del taller',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              'Gestiona la bandeja de incidentes, asigna tecnico y deja visible el punto donde se integrara la pasarela de pago.',
              style: TextStyle(color: Color(0xFF6F655B), height: 1.5),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _FilterChip(
                  label: 'Bandeja',
                  selected: _selectedFilter == 0,
                  onTap: () => setState(() => _selectedFilter = 0),
                ),
                _FilterChip(
                  label: 'Activos',
                  selected: _selectedFilter == 1,
                  onTap: () => setState(() => _selectedFilter = 1),
                ),
                _FilterChip(
                  label: 'Cerrados',
                  selected: _selectedFilter == 2,
                  onTap: () => setState(() => _selectedFilter = 2),
                ),
              ],
            ),
            const SizedBox(height: 18),
            if (controller.loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (requests.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'No hay solicitudes para este filtro.',
                    style: TextStyle(color: Color(0xFF6F655B)),
                  ),
                ),
              )
            else
              ...requests.map(
                (request) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _RequestCard(request: request),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _RequestCard extends StatelessWidget {
  const _RequestCard({required this.request});

  final EmergencyRequest request;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final formatter = DateFormat('dd/MM - HH:mm');
    final statusColor = _statusColor(request.estado);

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) =>
                  WorkshopRequestDetailScreen(requestId: request.id),
            ),
          );
        },
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
                request.clasificacionIa ?? 'Incidente sin clasificar',
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              Text(
                request.resumenIa ?? request.descripcion,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Color(0xFF5F554B), height: 1.45),
              ),
              const SizedBox(height: 12),
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
                  const SizedBox(width: 14),
                  const Icon(
                    Icons.engineering_outlined,
                    size: 18,
                    color: Color(0xFF6F655B),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      controller.technicianLabelFor(request),
                      style: const TextStyle(color: Color(0xFF6F655B)),
                    ),
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
              if (request.paymentReady) ...[
                const SizedBox(height: 12),
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF3E6),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                      'Cobro listo: este servicio ya puede abrir checkout cuando se conecte la pasarela real.',
                      style: TextStyle(color: Color(0xFF8B4C18), height: 1.45),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onTap(),
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
