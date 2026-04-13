import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, this.workshopMode = false});

  final bool workshopMode;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _baseUrlController = TextEditingController();
  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  bool _loadedFromState = false;

  @override
  void dispose() {
    _baseUrlController.dispose();
    _nameController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final user = controller.currentUser;

    if (!_loadedFromState) {
      _baseUrlController.text = controller.baseUrl;
      _nameController.text = user?.fullName ?? '';
      _usernameController.text = user?.username ?? '';
      _emailController.text = user?.email ?? '';
      _loadedFromState = true;
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.workshopMode ? 'Cuenta de taller' : 'Configuracion mobile'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesion',
            onPressed: controller.loading ? null : _logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          if (widget.workshopMode) ...[
            Card(
              color: const Color(0xFFFFF3E6),
              child: const Padding(
                padding: EdgeInsets.all(18),
                child: Text(
                  'La cuenta de taller ya puede registrarse e iniciar sesion desde mobile, pero la operacion principal del taller sigue siendo el dashboard web.',
                  style: TextStyle(height: 1.5),
                ),
              ),
            ),
            const SizedBox(height: 14),
          ],
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Backend',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _baseUrlController,
                    decoration: const InputDecoration(
                      labelText: 'Base URL',
                      hintText: 'http://10.0.2.2:8000',
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'En Android Emulator usa 10.0.2.2. En dispositivo fisico cambia esta URL por la IP de tu computadora en la misma red.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF6F655B), height: 1.45),
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      FilledButton(
                        onPressed: controller.loading ? null : _saveBaseUrl,
                        child: const Text('Guardar URL'),
                      ),
                      FilledButton.tonal(
                        onPressed: controller.loading ? null : _pingBackend,
                        child: const Text('Probar conexion'),
                      ),
                    ],
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
                    widget.workshopMode ? 'Perfil del taller' : 'Perfil del cliente',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _nameController,
                    decoration: InputDecoration(
                      labelText: widget.workshopMode ? 'Nombre del taller' : 'Nombre completo',
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
                    onPressed: controller.loading ? null : _saveProfile,
                    child: const Text('Actualizar perfil'),
                  ),
                ],
              ),
            ),
          ),
          if (!widget.workshopMode) ...[
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Vehiculos',
                            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                          ),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: controller.loading ? null : _showVehicleDialog,
                          icon: const Icon(Icons.add),
                          label: const Text('Registrar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    if (controller.vehicles.isEmpty)
                      const Text(
                        'No hay vehiculos registrados todavia.',
                        style: TextStyle(color: Color(0xFF6F655B)),
                      )
                    else
                      ...controller.vehicles.map(
                        (vehicle) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8F4ED),
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(color: const Color(0xFFE5D8C9)),
                            ),
                            child: ListTile(
                              leading: const CircleAvatar(
                                backgroundColor: Color(0xFFFFE2CC),
                                child: Icon(Icons.directions_car_filled_outlined),
                              ),
                              title: Text(vehicle.placa, style: const TextStyle(fontWeight: FontWeight.w700)),
                              subtitle: Text(
                                '${vehicle.marca} ${vehicle.modelo}${vehicle.color.isNotEmpty ? ' · ${vehicle.color}' : ''}',
                              ),
                              trailing: Text('#${vehicle.remoteId ?? '-'}'),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _saveBaseUrl() async {
    final controller = context.read<AppController>();
    try {
      await controller.saveBaseUrl(_baseUrlController.text);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('URL del backend guardada.')),
      );
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  Future<void> _pingBackend() async {
    final controller = context.read<AppController>();
    try {
      final message = await controller.testConnection();
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  Future<void> _saveProfile() async {
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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Perfil actualizado.')),
      );
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  Future<void> _logout() async {
    await context.read<AppController>().logout();
  }

  Future<void> _showVehicleDialog() async {
    final plateController = TextEditingController();
    final brandController = TextEditingController();
    final modelController = TextEditingController();
    final colorController = TextEditingController();

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Registrar vehiculo'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: plateController, decoration: const InputDecoration(labelText: 'Placa')),
                const SizedBox(height: 10),
                TextField(controller: brandController, decoration: const InputDecoration(labelText: 'Marca')),
                const SizedBox(height: 10),
                TextField(controller: modelController, decoration: const InputDecoration(labelText: 'Modelo')),
                const SizedBox(height: 10),
                TextField(controller: colorController, decoration: const InputDecoration(labelText: 'Color')),
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
                try {
                  await context.read<AppController>().addVehicle(
                    placa: plateController.text.trim(),
                    marca: brandController.text.trim(),
                    modelo: modelController.text.trim(),
                    color: colorController.text.trim(),
                  );
                  if (!dialogContext.mounted) {
                    return;
                  }
                  Navigator.of(dialogContext).pop();
                  if (!mounted) {
                    return;
                  }
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Vehiculo registrado en el backend.')),
                  );
                } catch (error) {
                  _showMessage(error.toString());
                }
              },
              child: const Text('Guardar'),
            ),
          ],
        );
      },
    );

    plateController.dispose();
    brandController.dispose();
    modelController.dispose();
    colorController.dispose();
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
