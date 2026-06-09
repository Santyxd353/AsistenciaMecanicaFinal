import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import 'location_picker_screen.dart';
import 'request_detail_screen.dart';

class QuoteRequestScreen extends StatefulWidget {
  const QuoteRequestScreen({super.key});

  @override
  State<QuoteRequestScreen> createState() => _QuoteRequestScreenState();
}

class _QuoteRequestScreenState extends State<QuoteRequestScreen> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionController = TextEditingController();
  final _notesController = TextEditingController();
  final _audioRecorder = AudioRecorder();
  final _assistantPlayer = AudioPlayer();

  String? _audioPath;
  bool _recordingAudio = false;
  bool _transcribingAudio = false;
  List<String> _imagePaths = const [];

  String? _selectedVehicleId;
  double? _selectedLat;
  double? _selectedLng;

  @override
  void dispose() {
    _descriptionController.dispose();
    _notesController.dispose();
    _audioRecorder.dispose();
    _assistantPlayer.dispose();
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
                'Solicitar cotizaciones',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              const Text(
                'Describe el fallo de tu vehiculo y envia la solicitud a los talleres candidatos para comparar precios antes de elegir uno.',
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
                          ? 'Solo una cuenta de conductor puede solicitar cotizaciones.'
                          : 'Antes de solicitar cotizaciones debes registrar al menos un vehiculo.',
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
                                'Vehiculo',
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
                                'Fallo detectado',
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
                                  labelText: 'Descripcion del fallo',
                                  hintText:
                                      'Ejemplo: el auto vibra al frenar y quiero comparar precios de revision.',
                                ),
                                validator: (value) {
                                  if (value == null ||
                                      value.trim().length < 12) {
                                    return 'Describe el fallo con al menos 12 caracteres.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _toggleAudioRecording,
                                    icon: Icon(
                                      _recordingAudio
                                          ? Icons.stop_circle_outlined
                                          : Icons.mic_none_outlined,
                                    ),
                                    label: Text(
                                      _recordingAudio ? 'Detener audio' : 'Comando por voz',
                                    ),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImagesFromGallery,
                                    icon: const Icon(Icons.photo_library_outlined),
                                    label: const Text('Galería'),
                                  ),
                                  FilledButton.tonalIcon(
                                    onPressed: _pickImageFromCamera,
                                    icon: const Icon(Icons.photo_camera_outlined),
                                    label: const Text('Cámara'),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              if (_imagePaths.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text('Fotos adjuntas:', style: TextStyle(fontWeight: FontWeight.w800)),
                                      const SizedBox(height: 6),
                                      ..._imagePaths.map((p) => Text(p.split(RegExp(r'[\\/]')).last, style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12))),
                                    ],
                                  ),
                                ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _notesController,
                                maxLines: 3,
                                decoration: const InputDecoration(
                                  labelText: 'Notas adicionales',
                                  hintText:
                                      'Disponibilidad, presupuesto aproximado, zona preferida...',
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
                                      'Ubicacion de referencia',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 16,
                                      ),
                                    ),
                                  ),
                                  if (_selectedLat != null &&
                                      _selectedLng != null)
                                    const Icon(
                                      Icons.check_circle,
                                      color: Color(0xFF167B47),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                _selectedLat == null || _selectedLng == null
                                    ? 'Usaremos tu ubicacion para priorizar talleres cercanos.'
                                    : '${_selectedLat!.toStringAsFixed(6)}, ${_selectedLng!.toStringAsFixed(6)}',
                                style: const TextStyle(
                                  color: Color(0xFF6F655B),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  FilledButton.tonalIcon(
                                    onPressed: _loadCurrentLocation,
                                    icon: const Icon(Icons.my_location),
                                    label: const Text('Usar GPS'),
                                  ),
                                  OutlinedButton.icon(
                                    onPressed: _openMapPicker,
                                    icon: const Icon(Icons.map_outlined),
                                    label: const Text('Elegir en mapa'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: controller.loading
                              ? null
                              : () => _submit(controller, selectedVehicle),
                          icon: const Icon(Icons.request_quote_outlined),
                          label: const Text('Enviar para cotizar'),
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

  Future<void> _toggleAudioRecording() async {
    if (_recordingAudio) {
      final path = await _audioRecorder.stop();
      if (!mounted) return;
      setState(() {
        _recordingAudio = false;
        if (path != null && path.isNotEmpty) {
          _audioPath = path;
        }
      });
      await _transcribeAudio();
      return;
    }

    final hasPermission = await _audioRecorder.hasPermission();
    if (!hasPermission) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Concede permiso de microfono para grabar audio.'),
        ),
      );
      return;
    }

    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/cotizacion-${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _audioRecorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc),
      path: path,
    );
    if (!mounted) return;
    setState(() => _recordingAudio = true);
  }

  Future<void> _transcribeAudio() async {
    final audioPath = _audioPath;
    if (audioPath == null || audioPath.isEmpty) return;

    setState(() => _transcribingAudio = true);
    try {
      final text = await context.read<AppController>().transcribeEmergencyAudio(audioPath);
      if (!mounted) return;
      final currentDescription = _descriptionController.text.trim();
      final nextDescription = currentDescription.isEmpty
          ? text
          : '$currentDescription\n\nTranscripcion del audio: $text';
      _descriptionController.value = TextEditingValue(
        text: nextDescription,
        selection: TextSelection.collapsed(offset: nextDescription.length),
      );
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Audio transcrito. Revisa el texto antes de enviar.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) setState(() => _transcribingAudio = false);
    }
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
      if (!mounted) return;
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
      if (!mounted) return;
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

  Future<void> _submit(AppController controller, Vehicle? vehicle) async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (vehicle == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Selecciona un vehiculo.')));
      return;
    }
    final latitud = _selectedLat;
    final longitud = _selectedLng;
    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Selecciona una ubicacion de referencia.'),
        ),
      );
      return;
    }

    try {
      final request = await controller.submitQuoteRequest(
        vehicle: vehicle,
        description: _descriptionController.text,
        latitud: latitud,
        longitud: longitud,
        extraNotes: _notesController.text,
        imagePaths: _imagePaths,
        audioPath: _audioPath,
      );
      if (!mounted) return;
      _descriptionController.clear();
      _notesController.clear();
      setState(() {
        _selectedLat = null;
        _selectedLng = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Solicitud de cotizacion #${request.id} enviada.'),
        ),
      );
      await _playAssistantVoice(
        messageKey: 'request_sent',
        descripcion: _descriptionController.text,
      );
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => RequestDetailScreen(requestId: request.id),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  Future<void> _playAssistantVoice({
    required String messageKey,
    String? especialidad,
    String? descripcion,
    String? incidentType,
  }) async {
    try {
      final url = await context.read<AppController>().synthesizeAssistantVoice(
        messageKey: messageKey,
        especialidad: especialidad,
        descripcion: descripcion,
        incidentType: incidentType,
      );
      if (url == null || url.isEmpty) return;
      await _assistantPlayer.stop();
      await _assistantPlayer.play(UrlSource(url));
    } catch (_) {
      if (!mounted) return;
      final fallback =
          'Su cotización fue enviada. Pronto tendrá una notificación sobre su cotización.';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(fallback)));
    }
  }

  Future<void> _pickImagesFromGallery() async {
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(imageQuality: 85);
    if (images.isEmpty) return;
    setState(() {
      _imagePaths = [..._imagePaths, ...images.map((image) => image.path)];
    });
  }

  Future<void> _pickImageFromCamera() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (image == null) return;
    setState(() {
      _imagePaths = [..._imagePaths, image.path];
    });
  }
}
