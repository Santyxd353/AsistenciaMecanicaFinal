import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';

class WorkshopAccountScreen extends StatefulWidget {
  const WorkshopAccountScreen({super.key});

  @override
  State<WorkshopAccountScreen> createState() => _WorkshopAccountScreenState();
}

class _WorkshopAccountScreenState extends State<WorkshopAccountScreen> {
  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _workshopNameController = TextEditingController();
  final _addressController = TextEditingController();
  final _phoneController = TextEditingController();
  final _contactEmailController = TextEditingController();
  final _scheduleController = TextEditingController();
  final _specialtiesController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _siteController = TextEditingController();
  final _latController = TextEditingController();
  final _lngController = TextEditingController();

  int? _syncedUserId;
  int? _syncedWorkshopId;
  bool _notifAssignments = true;
  bool _notifPush = true;
  bool _notifReminders = true;
  bool _notifPayments = true;
  bool _weeklyReports = false;

  @override
  void dispose() {
    _nameController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _workshopNameController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _contactEmailController.dispose();
    _scheduleController.dispose();
    _specialtiesController.dispose();
    _descriptionController.dispose();
    _siteController.dispose();
    _latController.dispose();
    _lngController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final user = controller.currentUser;
    final workshop = controller.workshopProfile;

    if (_syncedUserId != user?.id) {
      _nameController.text = user?.fullName ?? '';
      _usernameController.text = user?.username ?? '';
      _emailController.text = user?.email ?? '';
      _syncedUserId = user?.id;
    }

    if (_syncedWorkshopId != workshop?.id) {
      _workshopNameController.text = workshop?.nombreComercial ?? '';
      _addressController.text = workshop?.direccion ?? '';
      _phoneController.text = workshop?.telefono ?? '';
      _contactEmailController.text = workshop?.emailContacto ?? '';
      _scheduleController.text = workshop?.horarioAtencion ?? '';
      _specialtiesController.text = workshop?.especialidades ?? '';
      _descriptionController.text = workshop?.descripcion ?? '';
      _siteController.text = workshop?.sitioWeb ?? '';
      _latController.text = workshop?.latitud?.toString() ?? '';
      _lngController.text = workshop?.longitud?.toString() ?? '';
      _notifAssignments = workshop?.notificacionesNuevasAsignaciones ?? true;
      _notifPush = workshop?.notificacionesPush ?? true;
      _notifReminders = workshop?.notificacionesRecordatorios ?? true;
      _notifPayments = workshop?.notificacionesPagos ?? true;
      _weeklyReports = workshop?.reportesSemanales ?? false;
      _syncedWorkshopId = workshop?.id;
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cuenta del taller'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesion',
            onPressed: controller.loading ? null : controller.logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Cuenta de acceso',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Nombre visible',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _usernameController,
                    decoration: const InputDecoration(labelText: 'Usuario'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'Correo'),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: controller.loading ? null : _saveAccount,
                    child: const Text('Guardar cuenta'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    workshop == null ? 'Registrar taller' : 'Perfil del taller',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _workshopNameController,
                    decoration: const InputDecoration(
                      labelText: 'Nombre comercial',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _addressController,
                    decoration: const InputDecoration(labelText: 'Direccion'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: 'Telefono'),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _contactEmailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(
                      labelText: 'Correo contacto',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _scheduleController,
                    decoration: const InputDecoration(
                      labelText: 'Horario de atencion',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _specialtiesController,
                    decoration: const InputDecoration(
                      labelText: 'Especialidades',
                      hintText: 'Grua, bateria, llantas',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _descriptionController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Descripcion comercial',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _siteController,
                    decoration: const InputDecoration(labelText: 'Sitio web'),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _latController,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          decoration: const InputDecoration(
                            labelText: 'Latitud',
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _lngController,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          decoration: const InputDecoration(
                            labelText: 'Longitud',
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Preferencias',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Nuevas asignaciones'),
                    value: _notifAssignments,
                    onChanged: (value) =>
                        setState(() => _notifAssignments = value),
                  ),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Push del sistema'),
                    value: _notifPush,
                    onChanged: (value) => setState(() => _notifPush = value),
                  ),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Recordatorios'),
                    value: _notifReminders,
                    onChanged: (value) =>
                        setState(() => _notifReminders = value),
                  ),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Alertas de pagos'),
                    value: _notifPayments,
                    onChanged: (value) =>
                        setState(() => _notifPayments = value),
                  ),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Reportes semanales'),
                    value: _weeklyReports,
                    onChanged: (value) =>
                        setState(() => _weeklyReports = value),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: controller.loading ? null : _saveWorkshop,
                    child: Text(
                      workshop == null ? 'Crear taller' : 'Guardar taller',
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _saveAccount() async {
    final controller = context.read<AppController>();
    try {
      await controller.updateProfile(
        username: _usernameController.text.trim(),
        email: _emailController.text.trim(),
        fullName: _nameController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Cuenta actualizada.')));
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  Future<void> _saveWorkshop() async {
    final controller = context.read<AppController>();
    try {
      await controller.saveWorkshopProfile(
        nombreComercial: _workshopNameController.text,
        direccion: _addressController.text,
        telefono: _phoneController.text,
        emailContacto: _contactEmailController.text,
        horarioAtencion: _scheduleController.text,
        especialidades: _specialtiesController.text,
        descripcion: _descriptionController.text,
        sitioWeb: _siteController.text,
        latitud: double.tryParse(_latController.text.trim()),
        longitud: double.tryParse(_lngController.text.trim()),
        notificacionesNuevasAsignaciones: _notifAssignments,
        notificacionesPush: _notifPush,
        notificacionesRecordatorios: _notifReminders,
        notificacionesPagos: _notifPayments,
        reportesSemanales: _weeklyReports,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Perfil del taller guardado.')),
      );
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  void _showMessage(String raw) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(raw.replaceFirst('Exception: ', ''))),
    );
  }
}
