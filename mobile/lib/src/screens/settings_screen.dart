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
    this.anio,
    required this.color,
    required this.photoPaths,
  });

  final String placa;
  final String marca;
  final String modelo;
  final int? anio;
  final String color;
  final List<String> photoPaths;
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  bool _loadedFromState = false;

  @override
  void dispose() {
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
      _nameController.text = user?.fullName ?? '';
      _usernameController.text = user?.username ?? '';
      _emailController.text = user?.email ?? '';
      _loadedFromState = true;
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.workshopMode ? 'Cuenta de taller' : 'Configuracion mobile',
        ),
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
                  Text(
                    widget.workshopMode
                        ? 'Perfil del taller'
                        : 'Perfil del cliente',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _nameController,
                    decoration: InputDecoration(
                      labelText: widget.workshopMode
                          ? 'Nombre del taller'
                          : 'Nombre completo',
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
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                            ),
                          ),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: controller.loading
                              ? null
                              : _showVehicleDialog,
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
                      ...controller.vehicles.map((vehicle) {
                        final imageProvider = _vehicleImageProvider(vehicle);
                        final detail = [
                          '${vehicle.marca} ${vehicle.modelo}'.trim(),
                          if (vehicle.anio != null) vehicle.anio.toString(),
                          if (vehicle.color.isNotEmpty) vehicle.color,
                        ].join(' · ');

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8F4ED),
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(
                                color: const Color(0xFFE5D8C9),
                              ),
                            ),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: const Color(0xFFFFE2CC),
                                backgroundImage: imageProvider,
                                child: imageProvider == null
                                    ? const Icon(
                                        Icons.directions_car_filled_outlined,
                                      )
                                    : null,
                              ),
                              title: Text(
                                vehicle.placa,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              subtitle: Text(detail),
                              trailing: Text('#${vehicle.remoteId ?? '-'}'),
                            ),
                          ),
                        );
                      }),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
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
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Perfil actualizado.')));
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
        anio: draft.anio,
        color: draft.color,
        photoPath: draft.photoPaths.isEmpty ? null : draft.photoPaths.first,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vehiculo registrado correctamente.')),
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

  ImageProvider<Object>? _vehicleImageProvider(Vehicle vehicle) {
    if (vehicle.photoPath != null && vehicle.photoPath!.isNotEmpty) {
      final file = File(vehicle.photoPath!);
      if (file.existsSync()) {
        return FileImage(file);
      }
    }
    if (vehicle.photoUrl != null && vehicle.photoUrl!.isNotEmpty) {
      return NetworkImage(vehicle.photoUrl!);
    }
    return null;
  }
}

class _VehicleDialog extends StatefulWidget {
  const _VehicleDialog();

  @override
  State<_VehicleDialog> createState() => _VehicleDialogState();
}

class _VehicleDialogState extends State<_VehicleDialog> {
  final _formKey = GlobalKey<FormState>();
  final _plateController = TextEditingController();
  final _brandController = TextEditingController();
  final _modelController = TextEditingController();
  final _yearController = TextEditingController();
  final _colorController = TextEditingController();
  List<String> _photoPaths = const [];
  VehiclePhotoPreview? _preview;
  String? _previewMessage;
  bool _analyzing = false;

  @override
  void dispose() {
    _plateController.dispose();
    _brandController.dispose();
    _modelController.dispose();
    _yearController.dispose();
    _colorController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Registrar vehiculo'),
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
                controller: _yearController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Año'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _colorController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Color'),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: const Color(0xFFFFE2CC),
                    backgroundImage: _photoPaths.isEmpty
                        ? null
                        : FileImage(File(_photoPaths.first)),
                    child: _photoPaths.isEmpty
                        ? const Icon(Icons.directions_car_filled_outlined)
                        : null,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        FilledButton.tonalIcon(
                          onPressed: _pickPhotosFromGallery,
                          icon: const Icon(Icons.photo_library_outlined),
                          label: const Text('Fotos'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () => _pickPhoto(ImageSource.camera),
                          icon: const Icon(Icons.photo_camera_outlined),
                          label: const Text('Camara'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: _photoPaths.isEmpty || _analyzing
                              ? null
                              : _analyzePhotos,
                          icon: const Icon(Icons.auto_awesome_outlined),
                          label: Text(
                            _analyzing ? 'Analizando...' : 'Analizar',
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (_photoPaths.isNotEmpty) ...[
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${_photoPaths.length} foto(s) cargada(s)',
                    style: const TextStyle(color: Color(0xFF6F655B)),
                  ),
                ),
              ],
              if (_preview != null || _previewMessage != null) ...[
                const SizedBox(height: 14),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFFAF5),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFF0E5D7)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Previsualizacion IA',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _previewMessage ??
                            'La IA relleno el formulario con una sugerencia editable.',
                        style: const TextStyle(height: 1.4),
                      ),
                      if (_preview != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          'Placa: ${_preview!.placa.isEmpty ? "-" : _preview!.placa}',
                        ),
                        Text(
                          'Marca: ${_preview!.marca.isEmpty ? "-" : _preview!.marca}',
                        ),
                        Text(
                          'Modelo: ${_preview!.modelo.isEmpty ? "-" : _preview!.modelo}',
                        ),
                        Text('Anio: ${_preview!.anio?.toString() ?? "-"}'),
                        Text(
                          'Color: ${_preview!.color.isEmpty ? "-" : _preview!.color}',
                        ),
                      ],
                    ],
                  ),
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
        FilledButton(onPressed: _submit, child: const Text('Guardar')),
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
        anio: int.tryParse(_yearController.text.trim()),
        color: _colorController.text.trim(),
        photoPaths: _photoPaths,
      ),
    );
  }

  Future<void> _pickPhotosFromGallery() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(imageQuality: 85);
    if (images.isEmpty) {
      return;
    }
    setState(() {
      _photoPaths = [
        ..._photoPaths,
        ...images.map((item) => item.path),
      ].take(4).toList();
    });
  }

  Future<void> _pickPhoto(ImageSource source) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: source, imageQuality: 85);
    if (image == null) {
      return;
    }
    setState(() {
      _photoPaths = [..._photoPaths, image.path].take(4).toList();
    });
  }

  Future<void> _analyzePhotos() async {
    setState(() {
      _analyzing = true;
    });
    try {
      final preview = await context
          .read<AppController>()
          .previewVehicleFromPhotos(_photoPaths);
      if (!mounted) {
        return;
      }
      setState(() {
        _preview = preview;
        _previewMessage = preview.resumen;
        if (preview.placa.isNotEmpty) {
          _plateController.text = preview.placa;
        }
        if (preview.marca.isNotEmpty) {
          _brandController.text = preview.marca;
        }
        if (preview.modelo.isNotEmpty) {
          _modelController.text = preview.modelo;
        }
        if (preview.anio != null) {
          _yearController.text = preview.anio.toString();
        }
        if (preview.color.isNotEmpty) {
          _colorController.text = preview.color;
        }
      });
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
        setState(() {
          _analyzing = false;
        });
      }
    }
  }

  FormFieldValidator<String> _requiredField(String message) {
    return (value) => value == null || value.trim().isEmpty ? message : null;
  }
}
