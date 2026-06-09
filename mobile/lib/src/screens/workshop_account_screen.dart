import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';
import 'location_picker_screen.dart';

typedef _WorkshopDay = String;

class WorkshopAccountScreen extends StatefulWidget {
  const WorkshopAccountScreen({super.key});

  @override
  State<WorkshopAccountScreen> createState() => _WorkshopAccountScreenState();
}

class _WorkshopAccountScreenState extends State<WorkshopAccountScreen> {
  static const List<_WorkshopDay> _days = <_WorkshopDay>[
    'Lunes',
    'Martes',
    'Miercoles',
    'Jueves',
    'Viernes',
    'Sabado',
    'Domingo',
  ];

  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _workshopNameController = TextEditingController();
  final _addressController = TextEditingController();
  final _phoneController = TextEditingController();
  final _contactEmailController = TextEditingController();
  final _specialtiesController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _siteController = TextEditingController();

  int? _syncedUserId;
  int? _syncedWorkshopId;
  bool _notifAssignments = true;
  bool _notifPush = true;
  bool _notifReminders = true;
  bool _notifPayments = true;
  bool _weeklyReports = false;
  List<int> _selectedSpecialtyIds = const [];
  List<int> _selectedVehicleTypeIds = const [];

  List<_WorkshopDay> _generalDays = const [
    'Lunes',
    'Martes',
    'Miercoles',
    'Jueves',
    'Viernes',
    'Sabado',
  ];
  TimeOfDay? _generalOpen = const TimeOfDay(hour: 8, minute: 0);
  TimeOfDay? _generalClose = const TimeOfDay(hour: 18, minute: 0);
  bool _specialEnabled = false;
  _WorkshopDay _specialDay = 'Domingo';
  TimeOfDay? _specialOpen = const TimeOfDay(hour: 7, minute: 0);
  TimeOfDay? _specialClose = const TimeOfDay(hour: 13, minute: 0);
  double? _selectedLat = -16.5;
  double? _selectedLng = -68.15;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<AppController>().loadWorkshopCatalogs();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _workshopNameController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _contactEmailController.dispose();
    _specialtiesController.dispose();
    _descriptionController.dispose();
    _siteController.dispose();
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
      _specialtiesController.text = workshop?.especialidades ?? '';
      _selectedSpecialtyIds = workshop?.especialidadIds ?? const [];
      _selectedVehicleTypeIds = workshop?.tipoVehiculoIds ?? const [];
      _descriptionController.text = workshop?.descripcion ?? '';
      _siteController.text = workshop?.sitioWeb ?? '';
      _selectedLat = workshop?.latitud ?? -16.5;
      _selectedLng = workshop?.longitud ?? -68.15;
      _notifAssignments = workshop?.notificacionesNuevasAsignaciones ?? true;
      _notifPush = workshop?.notificacionesPush ?? true;
      _notifReminders = workshop?.notificacionesRecordatorios ?? true;
      _notifPayments = workshop?.notificacionesPagos ?? true;
      _weeklyReports = workshop?.reportesSemanales ?? false;
      if (workshop != null) {
        _applySchedule(workshop.horarioAtencion);
      }
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
                  const SizedBox(height: 18),
                  const Text(
                    'Horario de atencion',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Marca los dias generales del taller y agrega un horario especial si un dia atiende distinto.',
                    style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _days.map((day) {
                      final selected = _generalDays.contains(day);
                      return FilterChip(
                        selected: selected,
                        label: Text(day),
                        onSelected: (_) => _toggleGeneralDay(day),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _TimePickerField(
                          label: 'Apertura general',
                          value: _formatTime(_generalOpen),
                          onTap: () => _pickTime(
                            initial: _generalOpen,
                            onSelected: (time) =>
                                setState(() => _generalOpen = time),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _TimePickerField(
                          label: 'Cierre general',
                          value: _formatTime(_generalClose),
                          onTap: () => _pickTime(
                            initial: _generalClose,
                            onSelected: (time) =>
                                setState(() => _generalClose = time),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Agregar horario especial'),
                    subtitle: const Text('Ejemplo: Domingo de 07:00 a 13:00.'),
                    value: _specialEnabled,
                    onChanged: (value) =>
                        setState(() => _specialEnabled = value),
                  ),
                  if (_specialEnabled) ...[
                    const SizedBox(height: 6),
                    DropdownButtonFormField<_WorkshopDay>(
                      key: ValueKey<_WorkshopDay>(_specialDay),
                      initialValue: _specialDay,
                      items: _days
                          .map(
                            (day) => DropdownMenuItem<_WorkshopDay>(
                              value: day,
                              child: Text(day),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        setState(() => _specialDay = value);
                      },
                      decoration: const InputDecoration(
                        labelText: 'Dia especial',
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _TimePickerField(
                            label: 'Apertura especial',
                            value: _formatTime(_specialOpen),
                            onTap: () => _pickTime(
                              initial: _specialOpen,
                              onSelected: (time) =>
                                  setState(() => _specialOpen = time),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _TimePickerField(
                            label: 'Cierre especial',
                            value: _formatTime(_specialClose),
                            onTap: () => _pickTime(
                              initial: _specialClose,
                              onSelected: (time) =>
                                  setState(() => _specialClose = time),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 10),
                  Text(
                    _buildScheduleSummary(),
                    style: const TextStyle(
                      color: Color(0xFF5F554B),
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _CatalogSelector(
                    title: 'Especialidades',
                    subtitle:
                        'Elige los servicios que atiende tu taller. Esto ayuda a asignarte solicitudes correctas.',
                    items: controller.workshopSpecialties,
                    selectedIds: _selectedSpecialtyIds,
                    emptyText: 'Cargando especialidades...',
                    onToggle: (id) => setState(() {
                      _selectedSpecialtyIds = _toggleId(
                        _selectedSpecialtyIds,
                        id,
                      );
                      _specialtiesController.text = controller
                          .workshopSpecialties
                          .where(
                            (item) => _selectedSpecialtyIds.contains(item.id),
                          )
                          .map((item) => item.nombre)
                          .join(', ');
                    }),
                  ),
                  const SizedBox(height: 12),
                  _CatalogSelector(
                    title: 'Tipos de vehiculo',
                    subtitle: 'Marca qué vehículos puede recibir el taller.',
                    items: controller.vehicleTypesCatalog,
                    selectedIds: _selectedVehicleTypeIds,
                    emptyText: 'Cargando tipos de vehiculo...',
                    onToggle: (id) => setState(() {
                      _selectedVehicleTypeIds = _toggleId(
                        _selectedVehicleTypeIds,
                        id,
                      );
                    }),
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
                  const SizedBox(height: 18),
                  const Text(
                    'Ubicacion del taller',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Selecciona la ubicacion exacta usando el mapa. Puedes usar tu ubicacion actual o mover el pin manualmente.',
                    style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
                  ),
                  const SizedBox(height: 12),
                  DecoratedBox(
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
                          const Text(
                            'Punto seleccionado',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _locationSummary,
                            style: const TextStyle(
                              color: Color(0xFF5F554B),
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            children: [
                              FilledButton.tonalIcon(
                                onPressed: _useCurrentLocation,
                                icon: const Icon(Icons.my_location),
                                label: const Text('Usar actual'),
                              ),
                              FilledButton.tonalIcon(
                                onPressed: _openMapPicker,
                                icon: const Icon(Icons.map_outlined),
                                label: const Text('Abrir mapa'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
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
    final missingFields = _missingWorkshopFields();
    if (missingFields.isNotEmpty) {
      _showMissingFields(missingFields);
      return;
    }

    try {
      await controller.saveWorkshopProfile(
        nombreComercial: _workshopNameController.text,
        direccion: _addressController.text,
        telefono: _phoneController.text,
        emailContacto: _contactEmailController.text,
        horarioAtencion: _buildScheduleSummary(),
        especialidades: _specialtiesController.text,
        descripcion: _descriptionController.text,
        sitioWeb: _siteController.text,
        latitud: _selectedLat,
        longitud: _selectedLng,
        especialidadIds: _selectedSpecialtyIds,
        tipoVehiculoIds: _selectedVehicleTypeIds,
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

  void _toggleGeneralDay(_WorkshopDay day) {
    setState(() {
      if (_generalDays.contains(day)) {
        _generalDays = _generalDays.where((item) => item != day).toList();
      } else {
        _generalDays = [..._generalDays, day]
          ..sort((a, b) => _days.indexOf(a).compareTo(_days.indexOf(b)));
      }
    });
  }

  List<int> _toggleId(List<int> ids, int id) {
    if (ids.contains(id)) {
      return ids.where((item) => item != id).toList();
    }
    return [...ids, id];
  }

  List<String> _missingWorkshopFields() {
    final missing = <String>[];
    if (_workshopNameController.text.trim().isEmpty) {
      missing.add('Nombre comercial del taller');
    }
    if (_addressController.text.trim().isEmpty) {
      missing.add('Direccion del taller');
    }
    if (_phoneController.text.trim().isEmpty) {
      missing.add('Telefono de contacto');
    }
    final email = _contactEmailController.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      missing.add('Correo de contacto valido');
    }
    final scheduleError = _validateSchedule();
    if (scheduleError != null) {
      missing.add(scheduleError);
    }
    if (_selectedSpecialtyIds.isEmpty) {
      missing.add('Al menos una especialidad');
    }
    if (_selectedVehicleTypeIds.isEmpty) {
      missing.add('Al menos un tipo de vehiculo');
    }
    if (_selectedLat == null || _selectedLng == null) {
      missing.add('Ubicacion del taller en el mapa');
    }
    return missing;
  }

  Future<void> _showMissingFields(List<String> fields) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Faltan datos del taller'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Completa estos campos antes de crear el taller:'),
            const SizedBox(height: 12),
            ...fields.map(
              (field) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• '),
                    Expanded(child: Text(field)),
                  ],
                ),
              ),
            ),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Entendido'),
          ),
        ],
      ),
    );
  }

  Future<void> _pickTime({
    required TimeOfDay? initial,
    required ValueChanged<TimeOfDay> onSelected,
  }) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: initial ?? const TimeOfDay(hour: 8, minute: 0),
    );
    if (picked == null) {
      return;
    }
    onSelected(picked);
  }

  String _formatTime(TimeOfDay? time) {
    if (time == null) {
      return 'Seleccionar';
    }
    final hours = time.hour.toString().padLeft(2, '0');
    final minutes = time.minute.toString().padLeft(2, '0');
    return '$hours:$minutes';
  }

  String _buildScheduleSummary() {
    final generalDays = _generalDays.join(', ');
    final generalOpen = _formatTime(_generalOpen);
    final generalClose = _formatTime(_generalClose);
    final parts = <String>[
      'Dias generales: $generalDays',
      'Horario general: $generalOpen-$generalClose',
    ];

    if (_specialEnabled) {
      parts.add(
        'Horario especial: $_specialDay ${_formatTime(_specialOpen)}-${_formatTime(_specialClose)}',
      );
    }

    return parts.join(' | ');
  }

  String? _validateSchedule() {
    if (_generalDays.isEmpty) {
      return 'Selecciona al menos un dia de atencion general.';
    }
    if (_generalOpen == null || _generalClose == null) {
      return 'Completa el horario general del taller.';
    }
    if (_compareTime(_generalOpen!, _generalClose!) >= 0) {
      return 'La hora de cierre general debe ser posterior a la apertura.';
    }
    if (_specialEnabled) {
      if (_specialOpen == null || _specialClose == null) {
        return 'Completa el horario especial.';
      }
      if (_compareTime(_specialOpen!, _specialClose!) >= 0) {
        return 'La hora de cierre especial debe ser posterior a la apertura.';
      }
    }
    return null;
  }

  int _compareTime(TimeOfDay left, TimeOfDay right) {
    final leftMinutes = left.hour * 60 + left.minute;
    final rightMinutes = right.hour * 60 + right.minute;
    return leftMinutes.compareTo(rightMinutes);
  }

  String get _locationSummary {
    if (_selectedLat == null || _selectedLng == null) {
      return 'Ubicacion pendiente';
    }
    return '${_selectedLat!.toStringAsFixed(6)}, ${_selectedLng!.toStringAsFixed(6)}';
  }

  Future<void> _useCurrentLocation() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      _showMessage('Activa la ubicacion del dispositivo para continuar.');
      return;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      _showMessage('No se concedieron permisos de ubicacion.');
      return;
    }

    final position = await Geolocator.getCurrentPosition();
    if (!mounted) {
      return;
    }
    setState(() {
      _selectedLat = position.latitude;
      _selectedLng = position.longitude;
    });
  }

  Future<void> _openMapPicker() async {
    final initial = (_selectedLat != null && _selectedLng != null)
        ? LatLng(_selectedLat!, _selectedLng!)
        : null;
    final picked = await Navigator.of(context).push<LatLng>(
      MaterialPageRoute<LatLng>(
        builder: (_) => LocationPickerScreen(initialLocation: initial),
      ),
    );

    if (picked == null || !mounted) {
      return;
    }

    setState(() {
      _selectedLat = picked.latitude;
      _selectedLng = picked.longitude;
    });
  }

  void _applySchedule(String raw) {
    final parsed = _parseSchedule(raw);
    _generalDays = parsed.generalDays;
    _generalOpen = parsed.generalOpen;
    _generalClose = parsed.generalClose;
    _specialEnabled = parsed.specialEnabled;
    _specialDay = parsed.specialDay;
    _specialOpen = parsed.specialOpen;
    _specialClose = parsed.specialClose;
  }

  _ParsedWorkshopSchedule _parseSchedule(String raw) {
    final fallback = _ParsedWorkshopSchedule(
      generalDays: const [
        'Lunes',
        'Martes',
        'Miercoles',
        'Jueves',
        'Viernes',
        'Sabado',
      ],
      generalOpen: const TimeOfDay(hour: 8, minute: 0),
      generalClose: const TimeOfDay(hour: 18, minute: 0),
      specialEnabled: false,
      specialDay: 'Domingo',
      specialOpen: const TimeOfDay(hour: 7, minute: 0),
      specialClose: const TimeOfDay(hour: 13, minute: 0),
    );

    final text = raw.trim();
    if (text.isEmpty) {
      return fallback;
    }

    final generalDaysMatch = RegExp(
      r'Dias generales:\s*([^|]+)',
      caseSensitive: false,
    ).firstMatch(text);
    final generalTimeMatch = RegExp(
      r'Horario general:\s*(\d{2}:\d{2})-(\d{2}:\d{2})',
      caseSensitive: false,
    ).firstMatch(text);
    final specialMatch = RegExp(
      r'Horario especial:\s*(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo)\s+(\d{2}:\d{2})-(\d{2}:\d{2})',
      caseSensitive: false,
    ).firstMatch(text);
    final legacyRangeMatch = RegExp(
      r'(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo)\s+a\s+(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo).*?(\d{2}:\d{2}).*?(\d{2}:\d{2})',
      caseSensitive: false,
    ).firstMatch(text);

    final generalDays = generalDaysMatch != null
        ? _parseDayList(generalDaysMatch.group(1)!)
        : legacyRangeMatch != null
        ? _expandDayRange(
            legacyRangeMatch.group(1)!,
            legacyRangeMatch.group(2)!,
          )
        : _parseDayList(text);

    final generalOpen = _parseTime(
      generalTimeMatch?.group(1) ?? legacyRangeMatch?.group(3),
    );
    final generalClose = _parseTime(
      generalTimeMatch?.group(2) ?? legacyRangeMatch?.group(4),
    );

    return _ParsedWorkshopSchedule(
      generalDays: generalDays.isEmpty ? fallback.generalDays : generalDays,
      generalOpen: generalOpen ?? fallback.generalOpen,
      generalClose: generalClose ?? fallback.generalClose,
      specialEnabled: specialMatch != null,
      specialDay: specialMatch?.group(1) ?? fallback.specialDay,
      specialOpen: _parseTime(specialMatch?.group(2)) ?? fallback.specialOpen,
      specialClose: _parseTime(specialMatch?.group(3)) ?? fallback.specialClose,
    );
  }

  List<_WorkshopDay> _parseDayList(String value) {
    return _days
        .where((day) => RegExp(day, caseSensitive: false).hasMatch(value))
        .toList();
  }

  List<_WorkshopDay> _expandDayRange(String start, String end) {
    final startIndex = _days.indexWhere(
      (day) => day.toLowerCase() == start.toLowerCase(),
    );
    final endIndex = _days.indexWhere(
      (day) => day.toLowerCase() == end.toLowerCase(),
    );
    if (startIndex == -1 || endIndex == -1 || startIndex > endIndex) {
      return <_WorkshopDay>[];
    }
    return _days.sublist(startIndex, endIndex + 1);
  }

  TimeOfDay? _parseTime(String? raw) {
    if (raw == null) {
      return null;
    }
    final parts = raw.split(':');
    if (parts.length != 2) {
      return null;
    }
    final hour = int.tryParse(parts.first);
    final minute = int.tryParse(parts.last);
    if (hour == null || minute == null) {
      return null;
    }
    return TimeOfDay(hour: hour, minute: minute);
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

class _TimePickerField extends StatelessWidget {
  const _TimePickerField({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label),
        child: Text(value),
      ),
    );
  }
}

class _CatalogSelector extends StatelessWidget {
  const _CatalogSelector({
    required this.title,
    required this.subtitle,
    required this.items,
    required this.selectedIds,
    required this.emptyText,
    required this.onToggle,
  });

  final String title;
  final String subtitle;
  final List<CatalogItem> items;
  final List<int> selectedIds;
  final String emptyText;
  final ValueChanged<int> onToggle;

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
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: const TextStyle(
                color: Color(0xFF6F655B),
                fontSize: 12,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 12),
            if (items.isEmpty)
              Text(emptyText, style: const TextStyle(color: Color(0xFF8D5524)))
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: items.map((item) {
                  final selected = selectedIds.contains(item.id);
                  return FilterChip(
                    selected: selected,
                    label: Text(item.nombre),
                    onSelected: (_) => onToggle(item.id),
                    selectedColor: const Color(0xFFEAD8C2),
                    checkmarkColor: const Color(0xFF322214),
                  );
                }).toList(),
              ),
          ],
        ),
      ),
    );
  }
}

class _ParsedWorkshopSchedule {
  const _ParsedWorkshopSchedule({
    required this.generalDays,
    required this.generalOpen,
    required this.generalClose,
    required this.specialEnabled,
    required this.specialDay,
    required this.specialOpen,
    required this.specialClose,
  });

  final List<_WorkshopDay> generalDays;
  final TimeOfDay generalOpen;
  final TimeOfDay generalClose;
  final bool specialEnabled;
  final _WorkshopDay specialDay;
  final TimeOfDay specialOpen;
  final TimeOfDay specialClose;
}
