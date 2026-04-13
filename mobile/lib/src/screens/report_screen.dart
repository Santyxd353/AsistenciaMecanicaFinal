import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  static const _incidentTypes = [
    'Bateria',
    'Llanta',
    'Motor',
    'Choque',
    'Otro',
  ];

  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _notesController = TextEditingController();
  final _latController = TextEditingController();
  final _lngController = TextEditingController();

  String _selectedIncident = _incidentTypes.first;
  String? _selectedVehicleId;
  List<String> _imagePaths = const [];
  String? _audioPath;

  @override
  void dispose() {
    _descriptionController.dispose();
    _notesController.dispose();
    _latController.dispose();
    _lngController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();
    final vehicles = controller.vehicles;
    if (_selectedVehicleId == null && vehicles.isNotEmpty) {
      _selectedVehicleId = vehicles.first.localId;
    }
    final selectedVehicle = _findSelectedVehicle(vehicles);

    return SafeArea(
      child: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 32),
            children: [
              const Text(
                'Nueva emergencia',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              const Text(
                'Envia el reporte del cliente al backend actual. Las fotos y el audio quedan capturados localmente hasta que se habilite carga de evidencias en la API.',
                style: TextStyle(color: Color(0xFF6F655B), height: 1.5),
              ),
              const SizedBox(height: 18),
              if (!controller.isDriver || vehicles.isEmpty)
                Card(
                  color: const Color(0xFFFFF3E6),
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Text(
                      !controller.isDriver
                          ? 'Solo una cuenta de cliente puede reportar emergencias desde mobile.'
                          : vehicles.isEmpty
                          ? 'Antes de reportar debes registrar al menos un vehiculo en Config.'
                          : 'Completa tu cuenta en Config para que el reporte tenga datos consistentes.',
                    ),
                  ),
                )
              else
                Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Vehiculo y tipo de incidente',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              const SizedBox(height: 14),
                              DropdownButtonFormField<String>(
                                initialValue: selectedVehicle?.localId,
                                decoration: const InputDecoration(labelText: 'Vehiculo registrado'),
                                items: vehicles
                                    .map(
                                      (vehicle) => DropdownMenuItem<String>(
                                        value: vehicle.localId,
                                        child: Text(vehicle.label),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (value) => setState(() => _selectedVehicleId = value),
                              ),
                              const SizedBox(height: 16),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: _incidentTypes
                                    .map(
                                      (type) => ChoiceChip(
                                        label: Text(type),
                                        selected: _selectedIncident == type,
                                        onSelected: (_) => setState(() => _selectedIncident = type),
                                      ),
                                    )
                                    .toList(),
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
                                'Describe el problema',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _descriptionController,
                                maxLines: 5,
                                decoration: const InputDecoration(
                                  labelText: 'Que esta pasando con el vehiculo',
                                  hintText: 'Ejemplo: el auto no enciende y se escucha un click click',
                                ),
                                validator: (value) {
                                  if (value == null || value.trim().length < 12) {
                                    return 'Describe mejor el incidente para ayudar al taller.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _notesController,
                                maxLines: 3,
                                decoration: const InputDecoration(
                                  labelText: 'Notas adicionales',
                                  hintText: 'Referencia del lugar, sintomas extra, contacto alterno...',
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
                              Row(
                                children: [
                                  const Expanded(
                                    child: Text(
                                      'Ubicacion',
                                      style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                                    ),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _loadCurrentLocation,
                                    icon: const Icon(Icons.my_location),
                                    label: const Text('Usar actual'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                              Row(
                                children: [
                                  Expanded(
                                    child: TextFormField(
                                      controller: _latController,
                                      keyboardType:
                                          const TextInputType.numberWithOptions(decimal: true, signed: true),
                                      decoration: const InputDecoration(labelText: 'Latitud'),
                                      validator: _validateCoordinate,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextFormField(
                                      controller: _lngController,
                                      keyboardType:
                                          const TextInputType.numberWithOptions(decimal: true, signed: true),
                                      decoration: const InputDecoration(labelText: 'Longitud'),
                                      validator: _validateCoordinate,
                                    ),
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
                              const Text(
                                'Adjuntos capturados en mobile',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImages,
                                    icon: const Icon(Icons.photo_library_outlined),
                                    label: const Text('Fotos'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _pickAudio,
                                    icon: const Icon(Icons.mic_none_outlined),
                                    label: const Text('Audio'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                              if (_imagePaths.isEmpty && (_audioPath == null || _audioPath!.isEmpty))
                                const Text(
                                  'No hay archivos seleccionados.',
                                  style: TextStyle(color: Color(0xFF6F655B)),
                                )
                              else
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (_imagePaths.isNotEmpty)
                                      Text('Fotos: ${_imagePaths.length} seleccionada(s)'),
                                    if (_audioPath != null) Text('Audio: ${_fileName(_audioPath!)}'),
                                  ],
                                ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: controller.loading ? null : () => _submit(controller, selectedVehicle),
                          icon: const Icon(Icons.send_outlined),
                          label: const Text('Enviar solicitud al backend'),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          if (controller.loading)
            const Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: LinearProgressIndicator(minHeight: 3),
            ),
        ],
      ),
    );
  }

  Vehicle? _findSelectedVehicle(List<Vehicle> vehicles) {
    for (final vehicle in vehicles) {
      if (vehicle.localId == _selectedVehicleId) {
        return vehicle;
      }
    }
    return vehicles.isNotEmpty ? vehicles.first : null;
  }

  Future<void> _loadCurrentLocation() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Activa la ubicacion del dispositivo para continuar.')),
      );
      return;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se concedieron permisos de ubicacion.')),
      );
      return;
    }

    final position = await Geolocator.getCurrentPosition();
    _latController.text = position.latitude.toStringAsFixed(6);
    _lngController.text = position.longitude.toStringAsFixed(6);
    setState(() {});
  }

  Future<void> _pickImages() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(imageQuality: 85);
    if (images.isEmpty) {
      return;
    }
    setState(() {
      _imagePaths = images.map((image) => image.path).toList();
    });
  }

  Future<void> _pickAudio() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['m4a', 'mp3', 'wav', 'aac'],
    );
    if (result == null || result.files.single.path == null) {
      return;
    }
    setState(() {
      _audioPath = result.files.single.path!;
    });
  }

  Future<void> _submit(AppController controller, Vehicle? vehicle) async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (vehicle == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona un vehiculo antes de enviar la solicitud.')),
      );
      return;
    }

    final latitud = double.tryParse(_latController.text.trim());
    final longitud = double.tryParse(_lngController.text.trim());
    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa una ubicacion valida.')),
      );
      return;
    }

    try {
      final request = await controller.submitEmergency(
        vehicle: vehicle,
        incidentType: _selectedIncident,
        description: _descriptionController.text,
        latitud: latitud,
        longitud: longitud,
        imagePaths: _imagePaths,
        audioPath: _audioPath,
        extraNotes: _notesController.text,
      );

      if (!mounted) {
        return;
      }

      _descriptionController.clear();
      _notesController.clear();
      _latController.clear();
      _lngController.clear();
      setState(() {
        _selectedIncident = _incidentTypes.first;
        _imagePaths = const [];
        _audioPath = null;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Solicitud #${request.id} enviada correctamente.')),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
      );
    }
  }

  String? _validateCoordinate(String? value) {
    if (value == null || double.tryParse(value.trim()) == null) {
      return 'Valor invalido';
    }
    return null;
  }

  String _fileName(String path) => path.split(RegExp(r'[\\/]')).last;
}
