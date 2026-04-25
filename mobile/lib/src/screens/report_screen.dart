import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import 'location_picker_screen.dart';

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

  String _selectedIncident = _incidentTypes.first;
  String? _selectedVehicleId;
  List<String> _imagePaths = const [];
  String? _audioPath;
  LatLng? _selectedLocation;
  bool _loadingCurrentLocation = false;

  @override
  void dispose() {
    _descriptionController.dispose();
    _notesController.dispose();
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
                'Completa la descripcion, selecciona el vehiculo y fija la ubicacion exacta desde el mapa para que el taller llegue al punto correcto.',
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
                                  labelText: 'Descripcion textual del incidente',
                                  hintText: 'Ejemplo: el auto no enciende y se escucha un click click',
                                ),
                                validator: (value) {
                                  if (value == null || value.trim().length < 12) {
                                    return 'Ingresa al menos 12 caracteres para describir el incidente.';
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
                              const Text(
                                'Ubicacion de asistencia',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              const SizedBox(height: 6),
                              const Text(
                                'Puedes usar tu ubicacion actual o abrir el mapa y mover el pin hasta el punto exacto donde quieres la asistencia.',
                                style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _loadingCurrentLocation ? null : _loadCurrentLocation,
                                    icon: _loadingCurrentLocation
                                        ? const SizedBox(
                                            width: 16,
                                            height: 16,
                                            child: CircularProgressIndicator(strokeWidth: 2.1),
                                          )
                                        : const Icon(Icons.my_location),
                                    label: Text(_loadingCurrentLocation ? 'Buscando...' : 'Usar mi ubicacion'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _openMapPicker,
                                    icon: const Icon(Icons.map_outlined),
                                    label: const Text('Elegir en el mapa'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                              if (_selectedLocation == null)
                                const _LocationPlaceholder()
                              else
                                _LocationPreview(
                                  location: _selectedLocation!,
                                  onEdit: _openMapPicker,
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
                                'Adjuntos del incidente',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                'Agrega fotografias del incidente y un audio descriptivo si lo tienes.',
                                style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImagesFromGallery,
                                    icon: const Icon(Icons.photo_library_outlined),
                                    label: const Text('Galeria'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImageFromCamera,
                                    icon: const Icon(Icons.photo_camera_outlined),
                                    label: const Text('Camara'),
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
                                    if (_imagePaths.isNotEmpty) _AttachmentList(title: 'Fotografias', paths: _imagePaths),
                                    if (_audioPath != null) _AttachmentList(title: 'Audio descriptivo', paths: [_audioPath!]),
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
      _showMessage('Activa la ubicacion del dispositivo para continuar.');
      return;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      _showMessage('No se concedieron permisos de ubicacion.');
      return;
    }

    setState(() => _loadingCurrentLocation = true);
    try {
      final position = await Geolocator.getCurrentPosition();
      setState(() {
        _selectedLocation = LatLng(position.latitude, position.longitude);
      });
    } finally {
      if (mounted) {
        setState(() => _loadingCurrentLocation = false);
      }
    }
  }

  Future<void> _openMapPicker() async {
    final selected = await Navigator.of(context).push<LatLng>(
      MaterialPageRoute<LatLng>(
        builder: (_) => LocationPickerScreen(initialLocation: _selectedLocation),
      ),
    );

    if (selected == null || !mounted) {
      return;
    }

    setState(() => _selectedLocation = selected);
  }

  Future<void> _pickImagesFromGallery() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(imageQuality: 85);
    if (images.isEmpty) {
      return;
    }
    setState(() {
      _imagePaths = [..._imagePaths, ...images.map((image) => image.path)];
    });
  }

  Future<void> _pickImageFromCamera() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (image == null) {
      return;
    }
    setState(() {
      _imagePaths = [..._imagePaths, image.path];
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
      _showMessage('Selecciona un vehiculo antes de enviar la solicitud.');
      return;
    }

    final location = _selectedLocation;
    if (location == null) {
      _showMessage('Selecciona la ubicacion exacta antes de enviar la solicitud.');
      return;
    }

    try {
      final request = await controller.submitEmergency(
        vehicle: vehicle,
        incidentType: _selectedIncident,
        description: _descriptionController.text,
        latitud: location.latitude,
        longitud: location.longitude,
        imagePaths: _imagePaths,
        audioPath: _audioPath,
        extraNotes: _notesController.text,
      );

      if (!mounted) {
        return;
      }

      _descriptionController.clear();
      _notesController.clear();
      setState(() {
        _selectedIncident = _incidentTypes.first;
        _imagePaths = const [];
        _audioPath = null;
        _selectedLocation = null;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Solicitud #${request.id} enviada correctamente.')),
      );
    } catch (error) {
      _showMessage(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

class _LocationPlaceholder extends StatelessWidget {
  const _LocationPlaceholder();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: Color(0xFFFFE2CC),
              child: Icon(Icons.location_searching_outlined),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Todavia no elegiste un punto.',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Usa tu ubicacion actual o abre el mapa para fijar el pin exactamente donde necesitas la asistencia.',
                    style: TextStyle(color: Color(0xFF6F655B), height: 1.35),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LocationPreview extends StatelessWidget {
  const _LocationPreview({
    required this.location,
    required this.onEdit,
  });

  final LatLng location;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFFFFAF5),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF0E5D7)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Punto confirmado',
                    style: TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                TextButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_location_alt_outlined),
                  label: const Text('Mover pin'),
                ),
              ],
            ),
            Text(
              '${location.latitude.toStringAsFixed(6)}, ${location.longitude.toStringAsFixed(6)}',
              style: const TextStyle(color: Color(0xFF6F655B)),
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                height: 180,
                child: IgnorePointer(
                  child: FlutterMap(
                    options: MapOptions(
                      initialCenter: location,
                      initialZoom: 16,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.example.mobile',
                        maxZoom: 19,
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: location,
                            width: 54,
                            height: 54,
                            child: const Icon(
                              Icons.location_pin,
                              color: Color(0xFFC65A16),
                              size: 44,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AttachmentList extends StatelessWidget {
  const _AttachmentList({required this.title, required this.paths});

  final String title;
  final List<String> paths;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFFFFFAF5),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFF0E5D7)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$title: ${paths.length}', style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              ...paths.map(
                (path) => Text(
                  path.split(RegExp(r'[\\/]')).last,
                  style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
