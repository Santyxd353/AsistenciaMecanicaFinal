import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:flutter/material.dart';
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
  final _audioRecorder = AudioRecorder();

  String _selectedIncident = _incidentTypes.first;
  String? _selectedVehicleId;
  List<String> _imagePaths = const [];
  String? _audioPath;
  bool _recordingAudio = false;
  double? _selectedLat;
  double? _selectedLng;

  @override
  void dispose() {
    _descriptionController.dispose();
    _notesController.dispose();
    _audioRecorder.dispose();
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
                'Completa la descripcion, ubicacion y adjuntos del incidente. Las fotos y el audio quedan visibles en el detalle mobile de la solicitud.',
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
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                              const SizedBox(height: 14),
                              DropdownButtonFormField<String>(
                                initialValue: selectedVehicle?.localId,
                                decoration: const InputDecoration(
                                  labelText: 'Vehiculo registrado',
                                ),
                                items: vehicles
                                    .map(
                                      (vehicle) => DropdownMenuItem<String>(
                                        value: vehicle.localId,
                                        child: Text(vehicle.label),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (value) =>
                                    setState(() => _selectedVehicleId = value),
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
                                        onSelected: (_) => setState(
                                          () => _selectedIncident = type,
                                        ),
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
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _descriptionController,
                                maxLines: 5,
                                decoration: const InputDecoration(
                                  labelText:
                                      'Descripcion textual del incidente',
                                  hintText:
                                      'Ejemplo: el auto no enciende y se escucha un click click',
                                ),
                                validator: (value) {
                                  if (value == null ||
                                      value.trim().length < 12) {
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
                                  hintText:
                                      'Referencia del lugar, sintomas extra, contacto alterno...',
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
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 16,
                                      ),
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
                              FilledButton.tonalIcon(
                                onPressed: _openMapPicker,
                                icon: const Icon(Icons.map_outlined),
                                label: const Text('Elegir en mapa'),
                              ),
                              const SizedBox(height: 14),
                              Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFFAF5),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: const Color(0xFFF0E5D7),
                                  ),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Punto seleccionado',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      _selectedLat == null || _selectedLng == null
                                          ? 'Todavia no elegiste una ubicacion.'
                                          : '${_selectedLat!.toStringAsFixed(6)}, ${_selectedLng!.toStringAsFixed(6)}',
                                      style: const TextStyle(
                                        color: Color(0xFF6F655B),
                                        height: 1.4,
                                      ),
                                    ),
                                  ],
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
                                'Adjuntos del incidente',
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                'Agrega fotografias del vehiculo y un audio descriptivo si lo tienes.',
                                style: TextStyle(
                                  color: Color(0xFF6F655B),
                                  height: 1.4,
                                ),
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImagesFromGallery,
                                    icon: const Icon(
                                      Icons.photo_library_outlined,
                                    ),
                                    label: const Text('Galeria'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImageFromCamera,
                                    icon: const Icon(
                                      Icons.photo_camera_outlined,
                                    ),
                                    label: const Text('Camara'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _toggleAudioRecording,
                                    icon: Icon(
                                      _recordingAudio
                                          ? Icons.stop_circle_outlined
                                          : Icons.mic_none_outlined,
                                    ),
                                    label: Text(
                                      _recordingAudio
                                          ? 'Detener audio'
                                          : 'Grabar audio',
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                              if (_recordingAudio)
                                const Padding(
                                  padding: EdgeInsets.only(bottom: 10),
                                  child: Text(
                                    'Grabando audio descriptivo...',
                                    style: TextStyle(
                                      color: Color(0xFF9A4F2C),
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              if (_imagePaths.isEmpty &&
                                  (_audioPath == null || _audioPath!.isEmpty))
                                const Text(
                                  'No hay archivos seleccionados.',
                                  style: TextStyle(color: Color(0xFF6F655B)),
                                )
                              else
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (_imagePaths.isNotEmpty)
                                      _AttachmentList(
                                        title: 'Fotografias',
                                        paths: _imagePaths,
                                      ),
                                    if (_audioPath != null)
                                      _AttachmentList(
                                        title: 'Audio descriptivo',
                                        paths: [_audioPath!],
                                      ),
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
                          onPressed: controller.loading
                              ? null
                              : () => _submit(controller, selectedVehicle),
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
        const SnackBar(
          content: Text('Activa la ubicacion del dispositivo para continuar.'),
        ),
      );
      return;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No se concedieron permisos de ubicacion.'),
        ),
      );
      return;
    }

    final position = await Geolocator.getCurrentPosition();
    setState(() {
      _selectedLat = position.latitude;
      _selectedLng = position.longitude;
    });
  }

  Future<void> _openMapPicker() async {
    final picked = await Navigator.of(context).push<LatLng>(
      MaterialPageRoute(
        builder: (_) => LocationPickerScreen(
          initialLocation: _selectedLat != null && _selectedLng != null
              ? LatLng(_selectedLat!, _selectedLng!)
              : null,
        ),
      ),
    );
    if (picked == null) {
      return;
    }
    setState(() {
      _selectedLat = picked.latitude;
      _selectedLng = picked.longitude;
    });
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
    final image = await picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
    );
    if (image == null) {
      return;
    }
    setState(() {
      _imagePaths = [..._imagePaths, image.path];
    });
  }

  Future<void> _toggleAudioRecording() async {
    if (_recordingAudio) {
      final path = await _audioRecorder.stop();
      if (!mounted) {
        return;
      }
      setState(() {
        _recordingAudio = false;
        if (path != null && path.isNotEmpty) {
          _audioPath = path;
        }
      });
      return;
    }

    final hasPermission = await _audioRecorder.hasPermission();
    if (!hasPermission) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Concede permiso de microfono para grabar audio.')),
      );
      return;
    }

    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/reporte-${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _audioRecorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc),
      path: path,
    );
    if (!mounted) {
      return;
    }
    setState(() => _recordingAudio = true);
  }

  Future<void> _submit(AppController controller, Vehicle? vehicle) async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (vehicle == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selecciona un vehiculo antes de enviar la solicitud.'),
        ),
      );
      return;
    }

    final latitud = _selectedLat;
    final longitud = _selectedLng;
    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selecciona una ubicacion valida usando GPS o el mapa.'),
        ),
      );
      return;
    }

    try {
      if (_recordingAudio) {
        final path = await _audioRecorder.stop();
        _recordingAudio = false;
        if (path != null && path.isNotEmpty) {
          _audioPath = path;
        }
      }
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
      setState(() {
        _selectedIncident = _incidentTypes.first;
        _imagePaths = const [];
        _audioPath = null;
        _selectedLat = null;
        _selectedLng = null;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Solicitud #${request.id} enviada correctamente.'),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
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
              Text(
                '$title: ${paths.length}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              ...paths.map(
                (path) => Text(
                  path.split(RegExp(r'[\\/]')).last,
                  style: const TextStyle(
                    color: Color(0xFF6F655B),
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
