import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class WorkshopTeamScreen extends StatelessWidget {
  const WorkshopTeamScreen({super.key, required this.onOpenAccount});

  final VoidCallback onOpenAccount;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: controller.refreshData,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Equipo mecanico',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                FilledButton.tonalIcon(
                  onPressed: controller.loading
                      ? null
                      : () => _showCreateTechnicianDialog(context),
                  icon: const Icon(Icons.person_add_alt_1_outlined),
                  label: const Text('Agregar'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Registra mecanicos y controla disponibilidad desde el movil del taller.',
              style: TextStyle(color: Color(0xFF6F655B), height: 1.5),
            ),
            const SizedBox(height: 16),
            if (!controller.hasWorkshopProfile && !controller.isAdmin)
              Card(
                color: const Color(0xFFFFF3E6),
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Primero completa el taller',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Sin un taller creado no se pueden registrar mecanicos.',
                        style: TextStyle(height: 1.5),
                      ),
                      const SizedBox(height: 14),
                      FilledButton(
                        onPressed: onOpenAccount,
                        child: const Text('Ir a cuenta'),
                      ),
                    ],
                  ),
                ),
              ),
            if (!controller.hasWorkshopProfile && !controller.isAdmin)
              const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _MetricCard(
                    title: 'Registrados',
                    value: '${controller.technicians.length}',
                    caption: 'Mecanicos visibles',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _MetricCard(
                    title: 'Disponibles',
                    value: '${controller.availableTechniciansCount}',
                    caption: 'Listos para asignar',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            if (controller.technicians.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'Todavia no hay mecanicos registrados.',
                    style: TextStyle(color: Color(0xFF6F655B)),
                  ),
                ),
              )
            else
              ...controller.technicians.map(
                (technician) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _TechnicianCard(technician: technician),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _showCreateTechnicianDialog(BuildContext context) async {
    final controller = context.read<AppController>();
    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController();
    final specialtyController = TextEditingController();

    final created = await showDialog<Technician?>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Registrar mecanico'),
        content: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Nombre'),
                validator: (value) => value == null || value.trim().isEmpty
                    ? 'Ingresa el nombre.'
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: specialtyController,
                decoration: const InputDecoration(labelText: 'Especialidad'),
                validator: (value) => value == null || value.trim().isEmpty
                    ? 'Ingresa la especialidad.'
                    : null,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () async {
              if (!(formKey.currentState?.validate() ?? false)) {
                return;
              }
              try {
                final createdTechnician = await controller.addTechnician(
                  nombre: nameController.text,
                  especialidad: specialtyController.text,
                );
                if (!dialogContext.mounted) {
                  return;
                }
                Navigator.of(dialogContext).pop(createdTechnician);
              } catch (error) {
                if (!dialogContext.mounted) {
                  return;
                }
                ScaffoldMessenger.of(dialogContext).showSnackBar(
                  SnackBar(
                    content: Text(
                      error.toString().replaceFirst('Exception: ', ''),
                    ),
                  ),
                );
              }
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );

    nameController.dispose();
    specialtyController.dispose();

    if (created != null && context.mounted) {
      final user = created.usuarioUsername;
      final password = created.passwordTemporal;
      final message = user != null && password != null
          ? 'Mecanico creado. Usuario: $user | Contrasena: $password'
          : 'Mecanico registrado correctamente.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
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
            const SizedBox(height: 10),
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

class _TechnicianCard extends StatelessWidget {
  const _TechnicianCard({required this.technician});

  final Technician technician;

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: technician.disponible
                  ? const Color(0xFFE4F5EA)
                  : const Color(0xFFFFE7D2),
              child: Icon(
                technician.disponible
                    ? Icons.check_circle_outline
                    : Icons.build_outlined,
                color: technician.disponible
                    ? const Color(0xFF167B47)
                    : const Color(0xFFC65A16),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    technician.nombre,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    technician.especialidad,
                    style: const TextStyle(color: Color(0xFF6F655B)),
                  ),
                ],
              ),
            ),
            Switch.adaptive(
              value: technician.disponible,
              onChanged: controller.loading
                  ? null
                  : (value) async {
                      try {
                        await controller.setTechnicianAvailability(
                          technician: technician,
                          disponible: value,
                        );
                      } catch (error) {
                        if (!context.mounted) {
                          return;
                        }
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              error.toString().replaceFirst('Exception: ', ''),
                            ),
                          ),
                        );
                      }
                    },
            ),
          ],
        ),
      ),
    );
  }
}
