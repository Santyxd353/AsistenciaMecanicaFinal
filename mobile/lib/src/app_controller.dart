import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';
import 'repositories.dart';
import 'services/push_notifications.dart';

class AppController extends ChangeNotifier {
  bool _initialized = false;
  bool _loading = false;
  String _baseUrl = LocalRepository.defaultBaseUrl;
  String? _accessToken;
  AppUser? _currentUser;
  List<Vehicle> _vehicles = const [];
  List<LocalRequestMeta> _requestMetas = const [];
  List<EmergencyRequest> _requests = const [];
  List<Technician> _technicians = const [];
  List<AppNotification> _notifications = const [];
  WorkshopProfile? _workshopProfile;
  WorkshopStats? _workshopStats;

  bool get initialized => _initialized;
  bool get loading => _loading;
  String get baseUrl => _baseUrl;
  String? get accessToken => _accessToken;
  AppUser? get currentUser => _currentUser;
  bool get isAuthenticated => _accessToken != null && _currentUser != null;
  bool get isDriver => _currentUser?.isDriver ?? false;
  bool get isWorkshopLike => _currentUser?.isWorkshopLike ?? false;
  bool get isAdmin => _currentUser?.role == 'admin';
  List<Vehicle> get vehicles => List.unmodifiable(_vehicles);
  List<LocalRequestMeta> get requestMetas => List.unmodifiable(_requestMetas);
  List<EmergencyRequest> get requests => List.unmodifiable(_requests);
  List<Technician> get technicians => List.unmodifiable(_technicians);
  List<AppNotification> get notifications => List.unmodifiable(_notifications);
  WorkshopProfile? get workshopProfile => _workshopProfile;
  WorkshopStats? get workshopStats => _workshopStats;
  bool get hasWorkshopProfile => _workshopProfile != null;
  List<EmergencyRequest> get activeRequests =>
      _requests.where((request) => !request.isClosed).toList();

  int? get workshopId => _workshopProfile?.id;

  List<EmergencyRequest> get workshopInboxRequests {
    if (_currentUser?.role == 'tecnico') {
      return _requests.where((request) => !request.isClosed).toList()..sort(
        (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
      );
    }
    final wid = workshopId;
    return _requests.where((request) {
      if (request.isClosed) {
        return false;
      }
      if (isAdmin) {
        return true;
      }
      return request.tallerId == null || request.tallerId == wid;
    }).toList()..sort(
      (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
    );
  }

  List<EmergencyRequest> get workshopManagedRequests {
    if (_currentUser?.role == 'tecnico') {
      return _requests.toList()..sort(
        (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
      );
    }
    final wid = workshopId;
    return _requests.where((request) {
      if (isAdmin) {
        return request.tallerId != null;
      }
      return request.tallerId == wid;
    }).toList()..sort(
      (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
    );
  }

  List<EmergencyRequest> get workshopClosedRequests =>
      workshopManagedRequests.where((request) => request.isClosed).toList();

  int get availableTechniciansCount =>
      _technicians.where((technician) => technician.disponible).length;

  int get paymentReadyCount =>
      workshopManagedRequests.where((request) => request.paymentReady).length;

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }

    _setLoading(true);
    final prefs = await SharedPreferences.getInstance();
    final storage = LocalRepository(prefs);
    final snapshot = storage.load();

    _baseUrl = snapshot.baseUrl;
    _accessToken = snapshot.accessToken;
    _currentUser = snapshot.currentUser;
    _vehicles = snapshot.vehicles;
    _requestMetas = snapshot.requestMetas;
    _notifications = snapshot.notifications;

    if (isAuthenticated) {
      try {
        await _refreshRemoteData(storage);
        await _registerPushNotifications();
      } catch (_) {
        _accessToken = null;
        _currentUser = null;
        await storage.clearSession();
      }
    }

    _initialized = true;
    _setLoading(false);
  }

  Future<void> refreshData() async {
    if (!isAuthenticated) {
      return;
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      await _refreshRemoteData(storage);
    });
  }

  Future<void> saveBaseUrl(String value) async {
    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      _baseUrl = normalizeBaseUrl(value);
      await storage.saveBaseUrl(_baseUrl);
      if (isAuthenticated) {
        await _refreshRemoteData(storage);
      }
    });
  }

  Future<String> testConnection() async {
    final payload = await ApiClient(
      baseUrl: _baseUrl,
      token: _accessToken,
    ).ping();
    return payload['message']?.toString() ?? 'Conexion establecida.';
  }

  Future<void> login({
    required String username,
    required String password,
  }) async {
    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final auth = await ApiClient(
        baseUrl: _baseUrl,
      ).login(username: username, password: password);
      await _applyAuth(storage: storage, auth: auth);
      await _refreshRemoteData(storage);
    });
  }

  Future<void> registerClient({
    required String username,
    required String email,
    required String fullName,
    required String password,
  }) async {
    await _register(
      path: '/api/v1/auth/register/client',
      username: username,
      email: email,
      fullName: fullName,
      password: password,
    );
  }

  Future<void> registerWorkshop({
    required String username,
    required String email,
    required String fullName,
    required String password,
  }) async {
    await _register(
      path: '/api/v1/auth/register/workshop',
      username: username,
      email: email,
      fullName: fullName,
      password: password,
    );
  }

  Future<void> updateProfile({
    required String username,
    required String email,
    required String fullName,
  }) async {
    if (!isAuthenticated) {
      return;
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final updated = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).updateMe(username: username, email: email, fullName: fullName);
      _currentUser = updated;
      await storage.saveSession(token: _accessToken!, user: updated);
      notifyListeners();
    });
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    final storage = LocalRepository(prefs);
    _accessToken = null;
    _currentUser = null;
    _vehicles = const [];
    _requestMetas = const [];
    _requests = const [];
    _technicians = const [];
    _notifications = const [];
    _workshopProfile = null;
    _workshopStats = null;
    await storage.clearSession();
    notifyListeners();
  }

  Future<void> addVehicle({
    required String placa,
    required String marca,
    required String modelo,
    int? anio,
    required String color,
    String? photoPath,
  }) async {
    if (!isAuthenticated) {
      return;
    }

    final normalizedPlate = placa.trim().toUpperCase();
    final normalizedBrand = marca.trim();
    final normalizedModel = modelo.trim();
    final normalizedColor = color.trim();

    if (normalizedPlate.isEmpty ||
        normalizedBrand.isEmpty ||
        normalizedModel.isEmpty) {
      throw ApiException('Placa, marca y modelo son obligatorios.');
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final draft = Vehicle(
        localId: 'vehicle-${DateTime.now().millisecondsSinceEpoch}',
        placa: normalizedPlate,
        marca: normalizedBrand,
        modelo: normalizedModel,
        anio: anio,
        color: normalizedColor,
        photoPath: photoPath,
      );
      final created = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).createVehicle(draft);
      _vehicles = [created, ..._vehicles];
      await storage.saveVehicles(_vehicles);
    });
  }

  Future<void> updateVehicle({
    required Vehicle vehicle,
    required String placa,
    required String marca,
    required String modelo,
    int? anio,
    required String color,
    String? photoPath,
  }) async {
    if (!isAuthenticated) {
      return;
    }

    final updatedDraft = Vehicle(
      localId: vehicle.localId,
      remoteId: vehicle.remoteId,
      placa: placa.trim().toUpperCase(),
      marca: marca.trim(),
      modelo: modelo.trim(),
      anio: anio,
      color: color.trim(),
      photoPath: photoPath,
      photoUrl: vehicle.photoUrl,
    );

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final updated = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).updateVehicle(updatedDraft);
      _vehicles = _vehicles
          .map((item) => item.localId == updated.localId ? updated : item)
          .toList();
      await storage.saveVehicles(_vehicles);
    });
  }

  Future<void> saveWorkshopProfile({
    required String nombreComercial,
    required String direccion,
    required String telefono,
    String? emailContacto,
    required String horarioAtencion,
    required String especialidades,
    String? descripcion,
    String? sitioWeb,
    double? latitud,
    double? longitud,
    bool? notificacionesNuevasAsignaciones,
    bool? notificacionesPush,
    bool? notificacionesRecordatorios,
    bool? notificacionesPagos,
    bool? reportesSemanales,
  }) async {
    if (!isAuthenticated || !isWorkshopLike) {
      return;
    }

    if (nombreComercial.trim().isEmpty ||
        direccion.trim().isEmpty ||
        telefono.trim().isEmpty) {
      throw ApiException(
        'Nombre comercial, direccion y telefono son obligatorios.',
      );
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);

      if (_workshopProfile == null) {
        _workshopProfile = await api.createWorkshop(
          nombreComercial: nombreComercial.trim(),
          direccion: direccion.trim(),
          telefono: telefono.trim(),
          emailContacto: _normalizeOptional(emailContacto),
          horarioAtencion: horarioAtencion.trim(),
          especialidades: especialidades.trim(),
          descripcion: _normalizeOptional(descripcion),
          sitioWeb: _normalizeOptional(sitioWeb),
          latitud: latitud,
          longitud: longitud,
        );
      } else {
        _workshopProfile = await api.updateWorkshop({
          'nombre_comercial': nombreComercial.trim(),
          'direccion': direccion.trim(),
          'telefono': telefono.trim(),
          'email_contacto': _normalizeOptional(emailContacto),
          'horario_atencion': horarioAtencion.trim(),
          'especialidades': especialidades.trim(),
          'descripcion': _normalizeOptional(descripcion),
          'sitio_web': _normalizeOptional(sitioWeb),
          'latitud': latitud,
          'longitud': longitud,
          if (notificacionesNuevasAsignaciones != null)
            'notificaciones_nuevas_asignaciones':
                notificacionesNuevasAsignaciones,
          if (notificacionesPush != null)
            'notificaciones_push': notificacionesPush,
          if (notificacionesRecordatorios != null)
            'notificaciones_recordatorios': notificacionesRecordatorios,
          if (notificacionesPagos != null)
            'notificaciones_pagos': notificacionesPagos,
          if (reportesSemanales != null)
            'reportes_semanales': reportesSemanales,
        });
      }

      _workshopStats = await api.fetchWorkshopStats();
      notifyListeners();
      await storage.saveVehicles(_vehicles);
      await storage.saveRequestMetas(_requestMetas);
      await storage.saveNotifications(_notifications);
    });
  }

  Future<Technician?> addTechnician({
    required String nombre,
    required String especialidad,
  }) async {
    if (!isAuthenticated || !isWorkshopLike) {
      return null;
    }

    if (_workshopProfile == null && !isAdmin) {
      throw ApiException('Primero registra el perfil del taller.');
    }

    Technician? created;
    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
      created = await api.createTechnician(
        nombre: nombre.trim(),
        especialidad: especialidad.trim(),
      );
      await _refreshRemoteData(storage);
    });
    return created;
  }

  Future<void> setTechnicianAvailability({
    required Technician technician,
    required bool disponible,
  }) async {
    if (!isAuthenticated || !isWorkshopLike) {
      return;
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
      await api.updateTechnicianAvailability(
        tecnicoId: technician.id,
        disponible: disponible,
      );
      await _refreshRemoteData(storage);
    });
  }

  Future<void> assignRequest({
    required EmergencyRequest request,
    required Technician technician,
  }) async {
    if (!isAuthenticated || !isWorkshopLike) {
      return;
    }

    if (!canWorkshopTakeRequest(request)) {
      throw ApiException('Esta solicitud no esta disponible para tu taller.');
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
      await api.updateRequestStatus(
        requestId: request.id,
        estado: 'asignada',
        tecnicoId: technician.id,
      );
      await _refreshRemoteData(storage);
    });
  }

  Future<void> advanceRequestStatus({
    required EmergencyRequest request,
    required String estado,
  }) async {
    final isMechanic = _currentUser?.role == 'tecnico';
    if (!isAuthenticated || (!isWorkshopLike && !isMechanic)) {
      return;
    }

    if (!canWorkshopManageRequest(request)) {
      throw ApiException('Esta solicitud no pertenece a tu operacion.');
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
      if (isMechanic) {
        await api.updateMechanicAssignmentStatus(
          requestId: request.id,
          estado: estado,
        );
      } else {
        await api.updateRequestStatus(requestId: request.id, estado: estado);
      }
      await _refreshRemoteData(storage);
    });
  }

  Future<EmergencyRequest> submitEmergency({
    required Vehicle vehicle,
    required String incidentType,
    required String description,
    required double latitud,
    required double longitud,
    required List<String> imagePaths,
    String? audioPath,
    String extraNotes = '',
  }) async {
    if (!isAuthenticated) {
      throw ApiException('Debes iniciar sesion para reportar una emergencia.');
    }

    late EmergencyRequest created;
    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final composedDescription = [
        'Vehiculo ${vehicle.placa} (${vehicle.marca} ${vehicle.modelo})',
        'Tipo de emergencia: $incidentType',
        description.trim(),
        if (extraNotes.trim().isNotEmpty)
          'Notas del conductor: ${extraNotes.trim()}',
        if (imagePaths.isNotEmpty || (audioPath?.isNotEmpty ?? false))
          'Adjuntos capturados desde Flutter: ${imagePaths.length} foto(s)${audioPath != null ? " y 1 audio" : ""}.',
      ].join('. ');

      final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
      created = await api.createRequest(
        descripcion: composedDescription,
        latitud: latitud,
        longitud: longitud,
        vehiculoId: vehicle.remoteId,
        incidentType: incidentType,
        extraNotes: extraNotes.trim(),
        imagePaths: imagePaths,
        audioPath: audioPath,
      );
      if (imagePaths.isNotEmpty) {
        created = await api.uploadRequestImages(
          requestId: created.id,
          imagePaths: imagePaths,
        );
      }
      if (audioPath != null && audioPath.isNotEmpty) {
        created = await api.uploadRequestAudio(
          requestId: created.id,
          audioPath: audioPath,
        );
      }

      final meta = LocalRequestMeta(
        requestId: created.id,
        vehicleLabel: vehicle.label,
        issueType: incidentType,
        imagePaths: imagePaths,
        audioPath: audioPath,
        extraNotes: extraNotes.trim(),
      );

      _requestMetas = [
        meta,
        ..._requestMetas.where((item) => item.requestId != created.id),
      ];
      await storage.saveRequestMetas(_requestMetas);
      await _refreshRemoteData(storage);
    });
    return created;
  }

  Future<void> cancelRequest(int requestId) async {
    if (!isAuthenticated) {
      return;
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final updated = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).cancelRequest(requestId);
      _replaceRequest(updated);
      _pushNotification(
        title: 'Solicitud cancelada',
        message: 'La solicitud #${updated.id} fue cancelada correctamente.',
        requestId: updated.id,
      );
      if (isDriver) {
        await _persistDriverState(storage);
      } else {
        await _refreshRemoteData(storage);
      }
    });
  }

  Future<void> payRequest(int requestId, {double? amount}) async {
    if (!isAuthenticated) {
      return;
    }

    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final updated = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).payRequest(requestId, amount: amount);
      _replaceRequest(updated);
      _pushNotification(
        title: 'Pago registrado',
        message: 'La solicitud #${updated.id} quedo marcada como pagada.',
        requestId: updated.id,
      );
      await _persistDriverState(storage);
    });
  }

  Future<VehiclePhotoPreview> previewVehicleFromPhotos(
    List<String> imagePaths,
  ) async {
    if (!isAuthenticated) {
      throw ApiException(
        'Debes iniciar sesion para analizar fotos del vehiculo.',
      );
    }

    late final VehiclePhotoPreview preview;
    await _executeWithLoading(() async {
      preview = await ApiClient(
        baseUrl: _baseUrl,
        token: _accessToken,
      ).previewVehicleFromPhotos(imagePaths);
    });
    return preview;
  }

  LocalRequestMeta? metaFor(int requestId) {
    for (final meta in _requestMetas) {
      if (meta.requestId == requestId) {
        return meta;
      }
    }
    return null;
  }

  String vehicleLabelFor(EmergencyRequest request) {
    if ((request.vehiculoPlaca?.trim().isNotEmpty ?? false)) {
      final detail = request.vehiculoDescripcion?.trim();
      return detail == null || detail.isEmpty
          ? request.vehiculoPlaca!.trim()
          : '${request.vehiculoPlaca!.trim()} - $detail';
    }

    if (request.vehiculoId != null) {
      for (final vehicle in _vehicles) {
        if (vehicle.remoteId == request.vehiculoId) {
          return vehicle.label;
        }
      }
    }
    return metaFor(request.id)?.vehicleLabel ?? 'Vehiculo no identificado';
  }

  EmergencyRequest requestById(int requestId) {
    return _requests.firstWhere(
      (request) => request.id == requestId,
      orElse: () => throw ApiException('La solicitud ya no esta disponible.'),
    );
  }

  String technicianLabelFor(EmergencyRequest request) {
    if ((request.tecnicoNombre?.trim().isNotEmpty ?? false)) {
      final specialty = request.tecnicoEspecialidad?.trim();
      return specialty == null || specialty.isEmpty
          ? request.tecnicoNombre!.trim()
          : '${request.tecnicoNombre!.trim()} - $specialty';
    }

    if (request.tecnicoId != null) {
      for (final technician in _technicians) {
        if (technician.id == request.tecnicoId) {
          return technician.label;
        }
      }
      return 'Tecnico #${request.tecnicoId}';
    }

    return 'Aun no asignado';
  }

  String workshopLabelFor(EmergencyRequest request) {
    if ((request.tallerNombre?.trim().isNotEmpty ?? false)) {
      return request.tallerNombre!.trim();
    }

    if (request.tallerId != null) {
      return 'Taller #${request.tallerId}';
    }

    return 'Pendiente de asignacion';
  }

  String etaLabelFor(EmergencyRequest request) {
    if (request.estado == 'cancelada') {
      return 'Cancelada';
    }
    if (request.estado == 'resuelta') {
      return 'Finalizada';
    }
    if (request.tiempoEstimadoMinutos == null) {
      return 'Pendiente';
    }
    if (request.tiempoEstimadoMinutos == 0) {
      return 'En puerta';
    }
    return '${request.tiempoEstimadoMinutos} min';
  }

  String paymentLabelFor(EmergencyRequest request) {
    return (request.estadoPago ?? 'pendiente') == 'pagado'
        ? 'Pagado'
        : 'Pendiente';
  }

  bool canWorkshopTakeRequest(EmergencyRequest request) {
    if (request.isClosed) {
      return false;
    }
    if (isAdmin) {
      return true;
    }
    final wid = workshopId;
    return wid != null && (request.tallerId == null || request.tallerId == wid);
  }

  bool canWorkshopManageRequest(EmergencyRequest request) {
    if (request.isClosed) {
      return false;
    }
    if (_currentUser?.role == 'tecnico') {
      return request.tecnicoId != null;
    }
    if (isAdmin) {
      return true;
    }
    final wid = workshopId;
    return wid != null && request.tallerId == wid;
  }

  Future<void> _register({
    required String path,
    required String username,
    required String email,
    required String fullName,
    required String password,
  }) async {
    await _executeWithLoading(() async {
      final prefs = await SharedPreferences.getInstance();
      final storage = LocalRepository(prefs);
      final auth = await ApiClient(baseUrl: _baseUrl).register(
        path: path,
        username: username,
        email: email,
        fullName: fullName,
        password: password,
      );
      await _applyAuth(storage: storage, auth: auth);
      await _refreshRemoteData(storage);
    });
  }

  Future<void> _applyAuth({
    required LocalRepository storage,
    required AuthPayload auth,
  }) async {
    _accessToken = auth.accessToken;
    _currentUser = auth.user;
    await storage.saveSession(token: auth.accessToken, user: auth.user);
    await _registerPushNotifications();
  }

  Future<void> _registerPushNotifications() async {
    final token = _accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    await PushNotificationsService.registerDevice(
      baseUrl: _baseUrl,
      accessToken: token,
      onForegroundMessage:
          ({required String title, required String message, int? requestId}) {
            _pushNotification(
              title: title,
              message: message,
              requestId: requestId,
            );
            notifyListeners();
            SharedPreferences.getInstance().then((prefs) {
              LocalRepository(prefs).saveNotifications(_notifications);
            });
          },
    );
  }

  Future<void> _refreshRemoteData(LocalRepository storage) async {
    if (!isAuthenticated) {
      return;
    }

    final previousRequests = {
      for (final request in _requests) request.id: request,
    };

    final api = ApiClient(baseUrl: _baseUrl, token: _accessToken);
    final remoteUser = await api.getMe();
    _currentUser = remoteUser;
    await storage.saveSession(token: _accessToken!, user: remoteUser);

    if (remoteUser.isDriver) {
      final remoteVehicles = await api.fetchVehicles(_vehicles);
      final remoteById = {
        for (final vehicle in remoteVehicles)
          if (vehicle.remoteId != null) vehicle.remoteId!: vehicle,
      };

      _vehicles = _vehicles
          .map((vehicle) {
            if (vehicle.remoteId != null &&
                remoteById.containsKey(vehicle.remoteId)) {
              return remoteById[vehicle.remoteId]!.copyWith(
                localId: vehicle.localId,
                photoPath: vehicle.photoPath,
                photoUrl: remoteById[vehicle.remoteId]!.photoUrl,
              );
            }
            return vehicle;
          })
          .where(
            (vehicle) =>
                vehicle.remoteId == null ||
                remoteById.containsKey(vehicle.remoteId),
          )
          .toList();

      for (final remote in remoteVehicles) {
        final exists = _vehicles.any(
          (vehicle) => vehicle.remoteId == remote.remoteId,
        );
        if (!exists) {
          _vehicles = [..._vehicles, remote];
        }
      }

      final requests = await api.fetchRequests();
      _technicians = await api.fetchTechnicians();
      final trackedIds = _requestMetas.map((meta) => meta.requestId).toSet();
      _requests =
          requests.where((request) => trackedIds.contains(request.id)).toList()
            ..sort(
              (left, right) =>
                  right.fechaCreacion.compareTo(left.fechaCreacion),
            );
      _workshopProfile = null;
      _workshopStats = null;

      _buildNotifications(previousRequests, _requests);
      await _persistDriverState(storage);
    } else if (remoteUser.role == 'tecnico') {
      _vehicles = const [];
      _requestMetas = const [];
      _workshopProfile = null;
      _workshopStats = null;
      _technicians = const [];
      _requests = await api.fetchMechanicAssignments()
        ..sort(
          (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
        );

      await storage.saveVehicles(_vehicles);
      await storage.saveRequestMetas(_requestMetas);
      await storage.saveNotifications(_notifications);
    } else if (remoteUser.isWorkshopLike) {
      _vehicles = const [];
      _requestMetas = const [];
      _workshopProfile = await api.fetchMyWorkshop();
      _workshopStats = _workshopProfile == null
          ? null
          : await api.fetchWorkshopStats();
      _technicians = await api.fetchTechnicians();
      final pending = await api.fetchWorkshopPendingRequests();
      final managed = await api.fetchWorkshopManagedRequests();
      final byId = {
        for (final request in [...pending, ...managed]) request.id: request,
      };
      _requests = byId.values.toList()
        ..sort(
          (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
        );

      await storage.saveVehicles(_vehicles);
      await storage.saveRequestMetas(_requestMetas);
      await storage.saveNotifications(_notifications);
    } else {
      _vehicles = const [];
      _requests = const [];
      _requestMetas = const [];
      _technicians = const [];
      _notifications = const [];
      _workshopProfile = null;
      _workshopStats = null;
      await storage.saveVehicles(_vehicles);
      await storage.saveRequestMetas(_requestMetas);
      await storage.saveNotifications(_notifications);
    }

    notifyListeners();
  }

  void _buildNotifications(
    Map<int, EmergencyRequest> previous,
    List<EmergencyRequest> current,
  ) {
    for (final request in current) {
      final old = previous[request.id];
      if (old == null) {
        _pushNotification(
          title: 'Nueva solicitud visible',
          message: 'La solicitud #${request.id} ya aparece en tu seguimiento.',
          requestId: request.id,
        );
        continue;
      }

      if (old.estado != request.estado) {
        _pushNotification(
          title: 'Cambio de estado',
          message:
              'La solicitud #${request.id} cambio a ${request.statusLabel}.',
          requestId: request.id,
        );
      }

      if (old.tecnicoNombre != request.tecnicoNombre &&
          request.tecnicoNombre != null) {
        _pushNotification(
          title: 'Tecnico asignado',
          message:
              'La solicitud #${request.id} fue asignada a ${request.tecnicoNombre}.',
          requestId: request.id,
        );
      }

      if (old.estadoPago != request.estadoPago &&
          request.estadoPago == 'pagado') {
        _pushNotification(
          title: 'Pago confirmado',
          message: 'La solicitud #${request.id} ya figura como pagada.',
          requestId: request.id,
        );
      }
    }
  }

  void _pushNotification({
    required String title,
    required String message,
    int? requestId,
  }) {
    final duplicate = _notifications.any(
      (item) =>
          item.title == title &&
          item.message == message &&
          item.requestId == requestId,
    );
    if (duplicate) {
      return;
    }

    _notifications = [
      AppNotification(
        id: 'notification-${DateTime.now().microsecondsSinceEpoch}',
        title: title,
        message: message,
        createdAt: DateTime.now(),
        requestId: requestId,
      ),
      ..._notifications,
    ].take(20).toList();
  }

  void _replaceRequest(EmergencyRequest updated) {
    _requests =
        _requests.map((item) => item.id == updated.id ? updated : item).toList()
          ..sort(
            (left, right) => right.fechaCreacion.compareTo(left.fechaCreacion),
          );
  }

  Future<void> _persistDriverState(LocalRepository storage) async {
    await storage.saveVehicles(_vehicles);
    await storage.saveRequestMetas(_requestMetas);
    await storage.saveNotifications(_notifications);
  }

  Future<void> _executeWithLoading(Future<void> Function() action) async {
    _setLoading(true);
    try {
      await action();
    } finally {
      _setLoading(false);
    }
  }

  void _setLoading(bool value) {
    _loading = value;
    notifyListeners();
  }

  String? _normalizeOptional(String? value) {
    final trimmed = value?.trim() ?? '';
    return trimmed.isEmpty ? null : trimmed;
  }
}
