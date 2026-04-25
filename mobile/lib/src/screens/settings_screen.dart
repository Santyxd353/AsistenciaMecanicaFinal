import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, this.workshopMode = false});

  final bool workshopMode;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _VehicleDraft {
  const _VehicleDraft({
    required this.placa,
    required this.marca,
    required this.modelo,
    required this.color,
    this.photoPath,
  });

  final String placa;
  final String marca;
  final String modelo;
  final String color;
  final String? photoPath;
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
                              title: Text(vehicle.placa, style: const TextStyle(fontWeight: FontWeight.w700)),
                              subtitle: Text(
                                '${vehicle.marca} ${vehicle.modelo}${vehicle.color.isNotEmpty ? ' - ${vehicle.color}' : ''}',
                              ),
                              leading: vehicle.photoPath == null || vehicle.photoPath!.isEmpty
                                  ? const CircleAvatar(
                                      backgroundColor: Color(0xFFFFE2CC),
                                      child: Icon(Icons.directions_car_filled_outlined),
                                    )
                                  : ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: Image.file(
                                        File(vehicle.photoPath!),
                                        width: 56,
                                        height: 56,
                                        fit: BoxFit.cover,
                                        errorBuilder: (_, _, _) => const CircleAvatar(
                                          backgroundColor: Color(0xFFFFE2CC),
                                          child: Icon(Icons.directions_car_filled_outlined),
                                        ),
                                      ),
                                    ),
                              trailing: IconButton(
                                tooltip: 'Editar vehiculo',
                                onPressed: controller.loading ? null : () => _editVehicle(vehicle),
                                icon: const Icon(Icons.edit_outlined),
                              ),
                            ),
                          ),
                        ),
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
                    const Text(
                      'Novedades',
                      style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                    ),
                    const SizedBox(height: 12),
                    if (controller.notifications.isEmpty)
                      const Text(
                        'Todavia no hay alertas nuevas.',
                        style: TextStyle(color: Color(0xFF6F655B)),
                      )
                    else
                      ...controller.notifications.take(6).map(
                        (notification) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFFAF5),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFF0E5D7)),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(notification.title, style: const TextStyle(fontWeight: FontWeight.w700)),
                                  const SizedBox(height: 4),
                                  Text(notification.message, style: const TextStyle(color: Color(0xFF6F655B), height: 1.4)),
                                ],
                              ),
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
    final controller = context.read<AppController>();

    final draft = await showDialog<_VehicleDraft>(
      context: context,
      builder: (_) => const _VehicleDialog(),
    );

    if (draft == null || !mounted) {
      return;
    }

    try {
      await controller.addVehicle(
        placa: draft.placa,
        marca: draft.marca,
        modelo: draft.modelo,
        color: draft.color,
        photoPath: draft.photoPath,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vehiculo registrado en el backend.')),
      );
    } catch (error) {
      _showMessage(error.toString());
    }
  }

  Future<void> _editVehicle(Vehicle vehicle) async {
    final controller = context.read<AppController>();
    final draft = await showDialog<_VehicleDraft>(
      context: context,
      builder: (_) => _VehicleDialog(
        title: 'Editar vehiculo',
        submitLabel: 'Actualizar',
        initialValue: _VehicleDraft(
          placa: vehicle.placa,
          marca: vehicle.marca,
          modelo: vehicle.modelo,
          color: vehicle.color,
          photoPath: vehicle.photoPath,
        ),
      ),
    );

    if (draft == null || !mounted) {
      return;
    }

    try {
      await controller.updateVehicle(
        vehicle: vehicle,
        placa: draft.placa,
        marca: draft.marca,
        modelo: draft.modelo,
        color: draft.color,
        photoPath: draft.photoPath,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vehiculo actualizado correctamente.')),
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

class _VehicleDialog extends StatefulWidget {
  const _VehicleDialog({
    this.title = 'Registrar vehiculo',
    this.submitLabel = 'Guardar',
    this.initialValue,
  });

  final String title;
  final String submitLabel;
  final _VehicleDraft? initialValue;

  @override
  State<_VehicleDialog> createState() => _VehicleDialogState();
}

class _VehicleDialogState extends State<_VehicleDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _plateController;
  late final TextEditingController _brandController;
  late final TextEditingController _modelController;
  late final TextEditingController _colorController;
  late String? _photoPath;

  @override
  void initState() {
    super.initState();
    _plateController = TextEditingController(text: widget.initialValue?.placa ?? '');
    _brandController = TextEditingController(text: widget.initialValue?.marca ?? '');
    _modelController = TextEditingController(text: widget.initialValue?.modelo ?? '');
    _colorController = TextEditingController(text: widget.initialValue?.color ?? '');
    _photoPath = widget.initialValue?.photoPath;
  }

  @override
  void dispose() {
    _plateController.dispose();
    _brandController.dispose();
    _modelController.dispose();
    _colorController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _plateController,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(labelText: 'Placa'),
                validator: _requiredField('Ingresa la placa.'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _brandController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Marca'),
                validator: _requiredField('Ingresa la marca.'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _modelController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Modelo'),
                validator: _requiredField('Ingresa el modelo.'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _colorController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Color'),
              ),
              const SizedBox(height: 14),
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Foto del vehiculo',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              const SizedBox(height: 10),
              if (_photoPath != null && _photoPath!.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.file(
                    File(_photoPath!),
                    height: 150,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => _VehiclePhotoPlaceholder(
                      onGallery: _pickPhotoFromGallery,
                      onCamera: _pickPhotoFromCamera,
                    ),
                  ),
                )
              else
                _VehiclePhotoPlaceholder(
                  onGallery: _pickPhotoFromGallery,
                  onCamera: _pickPhotoFromCamera,
                ),
              if (_photoPath != null && _photoPath!.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton.tonalIcon(
                      onPressed: _pickPhotoFromGallery,
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('Cambiar'),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: () => setState(() => _photoPath = null),
                      icon: const Icon(Icons.delete_outline),
                      label: const Text('Quitar'),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _submit,
          child: Text(widget.submitLabel),
        ),
      ],
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    Navigator.of(context).pop(
      _VehicleDraft(
        placa: _plateController.text.trim(),
        marca: _brandController.text.trim(),
        modelo: _modelController.text.trim(),
        color: _colorController.text.trim(),
        photoPath: _photoPath,
      ),
    );
  }

  Future<void> _pickPhotoFromGallery() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null || !mounted) {
      return;
    }
    setState(() => _photoPath = image.path);
  }

  Future<void> _pickPhotoFromCamera() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (image == null || !mounted) {
      return;
    }
    setState(() => _photoPath = image.path);
  }

  FormFieldValidator<String> _requiredField(String message) {
    return (value) => value == null || value.trim().isEmpty ? message : null;
  }
}

class _VehiclePhotoPlaceholder extends StatelessWidget {
  const _VehiclePhotoPlaceholder({
    required this.onGallery,
    required this.onCamera,
  });

  final VoidCallback onGallery;
  final VoidCallback onCamera;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Agrega una foto frontal o lateral para identificar mejor el vehiculo.',
              style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.tonalIcon(
                  onPressed: onGallery,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Galeria'),
                ),
                FilledButton.tonalIcon(
                  onPressed: onCamera,
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: const Text('Camara'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
