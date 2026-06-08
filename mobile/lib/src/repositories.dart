import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'app_config.dart';
import 'models.dart';

class LocalRepository {
  LocalRepository(this._prefs);

  static const _baseUrlKey = 'base_url';
  static const _tokenKey = 'access_token';
  static const _userKey = 'current_user';
  static const _vehiclesKey = 'vehicles';
  static const _requestMetasKey = 'request_metas';
  static const _notificationsKey = 'notifications';
  static String get defaultBaseUrl => AppConfig.defaultBaseUrl;

  final SharedPreferences _prefs;

  AppSnapshot load() {
    final userRaw = _prefs.getString(_userKey);
    final vehiclesRaw = _prefs.getString(_vehiclesKey);
    final requestsRaw = _prefs.getString(_requestMetasKey);
    final notificationsRaw = _prefs.getString(_notificationsKey);

    final user = userRaw == null
        ? null
        : AppUser.fromJson(jsonDecode(userRaw) as Map<String, dynamic>);
    final vehicles = vehiclesRaw == null
        ? <Vehicle>[]
        : (jsonDecode(vehiclesRaw) as List<dynamic>)
              .map((item) => Vehicle.fromJson(item as Map<String, dynamic>))
              .toList();
    final requestMetas = requestsRaw == null
        ? <LocalRequestMeta>[]
        : (jsonDecode(requestsRaw) as List<dynamic>)
              .map(
                (item) =>
                    LocalRequestMeta.fromJson(item as Map<String, dynamic>),
              )
              .toList();
    final notifications = notificationsRaw == null
        ? <AppNotification>[]
        : (jsonDecode(notificationsRaw) as List<dynamic>)
              .map(
                (item) =>
                    AppNotification.fromJson(item as Map<String, dynamic>),
              )
              .toList();

    final storedBaseUrl = _prefs.getString(_baseUrlKey);
    final normalizedBaseUrl = AppConfig.resolveStoredBaseUrl(storedBaseUrl);

    if (storedBaseUrl != null && normalizedBaseUrl != storedBaseUrl) {
      _prefs.setString(_baseUrlKey, normalizedBaseUrl);
    }

    return AppSnapshot(
      baseUrl: normalizedBaseUrl,
      accessToken: _prefs.getString(_tokenKey),
      currentUser: user,
      vehicles: vehicles,
      requestMetas: requestMetas,
      notifications: notifications,
    );
  }

  Future<void> saveBaseUrl(String value) async {
    await _prefs.setString(_baseUrlKey, AppConfig.normalizeBaseUrl(value));
  }

  Future<void> saveSession({
    required String token,
    required AppUser user,
  }) async {
    await _prefs.setString(_tokenKey, token);
    await _prefs.setString(_userKey, jsonEncode(user.toJson()));
  }

  Future<void> clearSession() async {
    await _prefs.remove(_tokenKey);
    await _prefs.remove(_userKey);
    await _prefs.remove(_vehiclesKey);
    await _prefs.remove(_requestMetasKey);
    await _prefs.remove(_notificationsKey);
  }

  Future<void> saveVehicles(List<Vehicle> vehicles) async {
    await _prefs.setString(
      _vehiclesKey,
      jsonEncode(vehicles.map((vehicle) => vehicle.toJson()).toList()),
    );
  }

  Future<void> saveRequestMetas(List<LocalRequestMeta> requestMetas) async {
    await _prefs.setString(
      _requestMetasKey,
      jsonEncode(requestMetas.map((meta) => meta.toJson()).toList()),
    );
  }

  Future<void> saveNotifications(List<AppNotification> notifications) async {
    await _prefs.setString(
      _notificationsKey,
      jsonEncode(
        notifications.map((notification) => notification.toJson()).toList(),
      ),
    );
  }
}

class ApiClient {
  ApiClient({required String baseUrl, this.token})
    : _baseUrl = AppConfig.normalizeBaseUrl(baseUrl);

  final String _baseUrl;
  final String? token;

  Uri _uri(String path) => Uri.parse('$_baseUrl$path');
  Uri buildUri(String path) => _uri(path);
  Map<String, String> authHeaders({bool json = false}) => _headers(json: json);
  String get baseUrl => _baseUrl;
  String? resolveAssetUrl(String? relativeUrl) {
    if (relativeUrl == null || relativeUrl.trim().isEmpty) {
      return null;
    }
    if (relativeUrl.startsWith('http://') ||
        relativeUrl.startsWith('https://')) {
      return relativeUrl;
    }
    return '$_baseUrl${relativeUrl.startsWith('/') ? relativeUrl : '/$relativeUrl'}';
  }

  Map<String, String> _headers({bool json = false}) {
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null && token!.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<void> registerDeviceToken(String fcmToken) async {
    final response = await http
        .post(
          _uri('/api/v1/dispositivos/token'),
          headers: _headers(json: true),
          body: jsonEncode({
            'token': fcmToken,
            'plataforma': kIsWeb
                ? 'web'
                : (Platform.isAndroid ? 'android' : 'mobile'),
          }),
        )
        .timeout(const Duration(seconds: 12));
    _decodeObject(response);
  }

  Future<Map<String, dynamic>> ping() async {
    final response = await http
        .get(_uri('/'))
        .timeout(const Duration(seconds: 8));
    return _decodeObject(response);
  }

  Future<AuthPayload> login({
    required String username,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/auth/login'),
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
          body:
              'username=${Uri.encodeQueryComponent(username)}&password=${Uri.encodeQueryComponent(password)}',
        )
        .timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AuthPayload> loginClient({
    required String email,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/auth/login/client'),
          headers: _headers(json: true),
          body: jsonEncode({
            'email': email.trim().toLowerCase(),
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AuthPayload> loginAdmin({
    required String email,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/auth/login/admin'),
          headers: _headers(json: true),
          body: jsonEncode({
            'email': email.trim().toLowerCase(),
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AuthPayload> loginWorker({
    required int tallerId,
    required String username,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/auth/login/worker'),
          headers: _headers(json: true),
          body: jsonEncode({
            'taller_id': tallerId,
            'username': username.trim(),
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<List<PublicWorkshop>> searchPublicWorkshops(String query) async {
    final response = await http
        .get(
          _uri(
            '/api/v1/talleres/public/search?q=${Uri.encodeQueryComponent(query.trim())}',
          ),
        )
        .timeout(const Duration(seconds: 30));
    return _decodeList(response).map(PublicWorkshop.fromApi).toList();
  }

  Future<List<SaaSPlan>> fetchPlans() async {
    final response = await http
        .get(_uri('/api/v1/plans/'))
        .timeout(const Duration(seconds: 45));
    return _decodeList(response).map(SaaSPlan.fromApi).toList();
  }

  Future<PlanCheckout> createPlanCheckout({
    required String planCodigo,
    required String email,
    required String nombreContacto,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/subscriptions/checkout'),
          headers: _headers(json: true),
          body: jsonEncode({
            'plan_codigo': planCodigo,
            'email': email.trim().toLowerCase(),
            'nombre_contacto': nombreContacto.trim(),
          }),
        )
        .timeout(const Duration(seconds: 12));
    return PlanCheckout.fromApi(_decodeObject(response));
  }

  Future<PlanPayment> payPlanCheckout(int checkoutId) async {
    final response = await http
        .post(
          _uri('/api/v1/subscriptions/checkout/$checkoutId/pay'),
          headers: _headers(json: true),
        )
        .timeout(const Duration(seconds: 12));
    return PlanPayment.fromApi(_decodeObject(response));
  }

  Future<AuthPayload> onboardWorkshop({
    required String onboardingToken,
    required String adminUsername,
    required String adminEmail,
    required String adminFullName,
    required String adminPassword,
    required String nombreComercial,
    required String direccion,
    required String telefono,
    required String emailContacto,
    required String horarioAtencion,
    required List<int> especialidadIds,
    String? descripcion,
    String? sitioWeb,
    double? latitud,
    double? longitud,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/onboarding/workshop'),
          headers: _headers(json: true),
          body: jsonEncode({
            'onboarding_token': onboardingToken,
            'admin': {
              'username': adminUsername.trim(),
              'email': adminEmail.trim().toLowerCase(),
              'full_name': adminFullName.trim(),
              'password': adminPassword,
            },
            'taller': {
              'nombre_comercial': nombreComercial.trim(),
              'direccion': direccion.trim(),
              'telefono': telefono.trim(),
              'email_contacto': emailContacto.trim(),
              'horario_atencion': horarioAtencion.trim(),
              'especialidad_ids': especialidadIds,
              'descripcion': descripcion?.trim(),
              'sitio_web': sitioWeb?.trim(),
              'latitud': latitud,
              'longitud': longitud,
            },
          }),
        )
        .timeout(const Duration(seconds: 20));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AuthPayload> register({
    required String path,
    required String username,
    required String email,
    required String fullName,
    required String password,
  }) async {
    final response = await http
        .post(
          _uri(path),
          headers: _headers(json: true),
          body: jsonEncode({
            'username': username,
            'email': email,
            'full_name': fullName,
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AppUser> getMe() async {
    final response = await http
        .get(_uri('/api/v1/auth/me'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    return AppUser.fromJson(_decodeObject(response));
  }

  Future<AppUser> updateMe({
    required String username,
    required String email,
    required String fullName,
  }) async {
    final response = await http
        .put(
          _uri('/api/v1/auth/me'),
          headers: _headers(json: true),
          body: jsonEncode({
            'username': username,
            'email': email,
            'full_name': fullName,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return AppUser.fromJson(_decodeObject(response));
  }

  Future<List<Vehicle>> fetchVehicles(List<Vehicle> localVehicles) async {
    final response = await http
        .get(_uri('/api/v1/vehiculos/'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    final localVehiclesByRemote = {
      for (final vehicle in localVehicles)
        if (vehicle.remoteId != null) vehicle.remoteId!: vehicle.localId,
    };
    final localPhotosByRemote = {
      for (final vehicle in localVehicles)
        if (vehicle.remoteId != null) vehicle.remoteId!: vehicle.photoPath,
    };

    return payload.map((item) {
      final id = item['id'] as int?;
      final fallbackLocalId =
          'vehicle-${id ?? DateTime.now().millisecondsSinceEpoch}';
      return Vehicle.fromApi(
        item,
        localId: id == null
            ? fallbackLocalId
            : (localVehiclesByRemote[id] ?? fallbackLocalId),
        photoPath: id == null ? null : localPhotosByRemote[id],
        photoUrl: resolveAssetUrl(item['foto_url']?.toString()),
      );
    }).toList();
  }

  Future<Vehicle> createVehicle(Vehicle vehicle) async {
    final response = await http
        .post(
          _uri('/api/v1/vehiculos/'),
          headers: _headers(json: true),
          body: jsonEncode({
            'placa': vehicle.placa,
            'marca': vehicle.marca,
            'modelo': vehicle.modelo,
            'color': vehicle.color,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final payload = _decodeObject(response);
    return Vehicle.fromApi(
      payload,
      localId: vehicle.localId,
      photoPath: vehicle.photoPath,
      photoUrl: resolveAssetUrl(payload['foto_url']?.toString()),
    );
  }

  Future<Vehicle> updateVehicle(Vehicle vehicle) async {
    if (vehicle.remoteId == null) {
      throw ApiException('El vehiculo aun no tiene identificador remoto.');
    }

    final response = await http
        .put(
          _uri('/api/v1/vehiculos/${vehicle.remoteId}'),
          headers: _headers(json: true),
          body: jsonEncode({
            'placa': vehicle.placa,
            'marca': vehicle.marca,
            'modelo': vehicle.modelo,
            'color': vehicle.color,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final payload = _decodeObject(response);
    return Vehicle.fromApi(
      payload,
      localId: vehicle.localId,
      photoPath: vehicle.photoPath,
      photoUrl: resolveAssetUrl(payload['foto_url']?.toString()),
    );
  }

  Future<VehiclePhotoPreview> previewVehicleFromPhotos(
    List<String> imagePaths,
  ) async {
    if (imagePaths.isEmpty) {
      throw ApiException('Debes seleccionar al menos una foto del vehiculo.');
    }

    final request = http.MultipartRequest(
      'POST',
      _uri('/api/v1/vehiculos/preview-from-photo'),
    );
    request.headers.addAll(_headers());
    for (final path in imagePaths.take(4)) {
      final file = File(path);
      if (file.existsSync()) {
        request.files.add(
          await http.MultipartFile.fromPath('fotos', file.path),
        );
      }
    }
    final response = await request.send().timeout(const Duration(seconds: 45));
    return VehiclePhotoPreview.fromApi(await _decodeObjectFromStream(response));
  }

  Future<List<VehicleRepairHistory>> fetchVehicleHistory(int vehicleId) async {
    final response = await http
        .get(
          _uri('/api/v1/vehiculos/$vehicleId/historial'),
          headers: _headers(),
        )
        .timeout(const Duration(seconds: 12));
    return _decodeList(response).map(VehicleRepairHistory.fromApi).toList();
  }

  Future<List<EmergencyRequest>> fetchRequests() async {
    final response = await http
        .get(_uri('/api/v1/solicitudes/'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(EmergencyRequest.fromApi).toList();
  }

  Future<List<EmergencyRequest>> fetchWorkshopPendingRequests() async {
    final response = await http
        .get(_uri('/api/v1/solicitudes/taller/pendientes'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(EmergencyRequest.fromApi).toList();
  }

  Future<List<EmergencyRequest>> fetchWorkshopManagedRequests() async {
    final response = await http
        .get(
          _uri('/api/v1/solicitudes/taller/mis-solicitudes'),
          headers: _headers(),
        )
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(EmergencyRequest.fromApi).toList();
  }

  Future<List<EmergencyRequest>> fetchMechanicAssignments() async {
    final response = await http
        .get(_uri('/api/v1/solicitudes/mis-asignaciones'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(EmergencyRequest.fromApi).toList();
  }

  Future<List<Technician>> fetchTechnicians() async {
    final response = await http
        .get(_uri('/api/v1/tecnicos/'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(Technician.fromApi).toList();
  }

  Future<WorkshopProfile?> fetchMyWorkshop() async {
    final response = await http
        .get(_uri('/api/v1/talleres/mi-taller'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    if (response.statusCode == 404) {
      return null;
    }
    return WorkshopProfile.fromApi(_decodeObject(response));
  }

  Future<WorkshopProfile> createWorkshop({
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
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/talleres/'),
          headers: _headers(json: true),
          body: jsonEncode({
            'nombre_comercial': nombreComercial,
            'direccion': direccion,
            'telefono': telefono,
            'email_contacto': emailContacto,
            'horario_atencion': horarioAtencion,
            'especialidades': especialidades,
            'descripcion': descripcion,
            'sitio_web': sitioWeb,
            'latitud': latitud,
            'longitud': longitud,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return WorkshopProfile.fromApi(_decodeObject(response));
  }

  Future<WorkshopProfile> updateWorkshop(Map<String, dynamic> payload) async {
    final response = await http
        .put(
          _uri('/api/v1/talleres/mi-taller'),
          headers: _headers(json: true),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 12));
    return WorkshopProfile.fromApi(_decodeObject(response));
  }

  Future<WorkshopStats?> fetchWorkshopStats() async {
    final response = await http
        .get(_uri('/api/v1/talleres/estadisticas'), headers: _headers())
        .timeout(const Duration(seconds: 12));
    if (response.statusCode == 404) {
      return null;
    }
    return WorkshopStats.fromApi(_decodeObject(response));
  }

  Future<Technician> createTechnician({
    required String nombre,
    required String especialidad,
    bool disponible = true,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/tecnicos/'),
          headers: _headers(json: true),
          body: jsonEncode({
            'nombre': nombre,
            'especialidad': especialidad,
            'disponible': disponible,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return Technician.fromApi(_decodeObject(response));
  }

  Future<Technician> updateTechnicianAvailability({
    required int tecnicoId,
    required bool disponible,
  }) async {
    final response = await http
        .patch(
          _uri(
            '/api/v1/tecnicos/$tecnicoId/disponibilidad?disponible=$disponible',
          ),
          headers: _headers(json: true),
        )
        .timeout(const Duration(seconds: 12));
    return Technician.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> createRequest({
    required String descripcion,
    required double latitud,
    required double longitud,
    int? vehiculoId,
    String? incidentType,
    String? extraNotes,
    List<String> imagePaths = const [],
    String? audioPath,
    String? clienteSyncId,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/solicitudes/'),
          headers: _headers(json: true),
          body: jsonEncode({
            'descripcion': descripcion,
            'latitud': latitud,
            'longitud': longitud,
            'estado': 'pendiente',
            if (vehiculoId != null) 'vehiculo_id': vehiculoId,
            if (clienteSyncId != null) 'cliente_sync_id': clienteSyncId,
          }),
        )
        .timeout(const Duration(seconds: 30));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  /// Variante para la cola offline: manda el payload completo (con
  /// `cliente_sync_id`) tal cual al backend. Backend dedupea por ese id.
  Future<EmergencyRequest> createRequestRaw(
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .post(
          _uri('/api/v1/solicitudes/'),
          headers: _headers(json: true),
          body: jsonEncode({...payload, 'estado': 'pendiente'}),
        )
        .timeout(const Duration(seconds: 30));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> uploadRequestAudio({
    required int requestId,
    required String audioPath,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      _uri('/api/v1/solicitudes/$requestId/audio'),
    );
    request.headers.addAll(_headers());
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));
    final response = await request.send().timeout(const Duration(seconds: 60));
    return EmergencyRequest.fromApi(await _decodeObjectFromStream(response));
  }

  Future<EmergencyRequest> uploadRequestImages({
    required int requestId,
    required List<String> imagePaths,
  }) async {
    if (imagePaths.isEmpty) {
      throw ApiException('Debes seleccionar al menos una foto.');
    }

    final request = http.MultipartRequest(
      'POST',
      _uri('/api/v1/solicitudes/$requestId/imagenes'),
    );
    request.headers.addAll(_headers());
    for (final path in imagePaths.take(6)) {
      final file = File(path);
      if (file.existsSync()) {
        request.files.add(
          await http.MultipartFile.fromPath('fotos', file.path),
        );
      }
    }
    final response = await request.send().timeout(const Duration(seconds: 60));
    return EmergencyRequest.fromApi(await _decodeObjectFromStream(response));
  }

  Future<EmergencyRequest> updateRequestStatus({
    required int requestId,
    required String estado,
    int? tecnicoId,
  }) async {
    var path =
        '/api/v1/solicitudes/$requestId/estado?estado=${Uri.encodeQueryComponent(estado)}';
    if (tecnicoId != null) {
      path += '&tecnico_id=$tecnicoId';
    }
    final response = await http
        .patch(_uri(path), headers: _headers(json: true), body: jsonEncode({}))
        .timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> updateMechanicAssignmentStatus({
    required int requestId,
    required String estado,
  }) async {
    final response = await http
        .patch(
          _uri(
            '/api/v1/solicitudes/mis-asignaciones/$requestId/estado?estado=${Uri.encodeQueryComponent(estado)}',
          ),
          headers: _headers(json: true),
          body: jsonEncode({}),
        )
        .timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> cancelRequest(int requestId) async {
    final response = await http
        .patch(
          _uri('/api/v1/solicitudes/$requestId/cancelar'),
          headers: _headers(json: true),
        )
        .timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> payRequest(int requestId, {double? amount}) async {
    final response = await http
        .post(
          _uri('/api/v1/solicitudes/$requestId/pago'),
          headers: _headers(json: true),
          body: jsonEncode({if (amount != null) 'monto': amount}),
        )
        .timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<EmergencyRequest> updateRequestCost(
    int requestId, {
    required double amount,
  }) async {
    final response = await http
        .patch(
          _uri('/api/v1/solicitudes/$requestId/costo'),
          headers: _headers(json: true),
          body: jsonEncode({'monto': amount}),
        )
        .timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Future<List<Cotizacion>> fetchCotizaciones(int requestId) async {
    final response = await http
        .get(
          _uri('/api/v1/cotizaciones/solicitudes/$requestId'),
          headers: _headers(),
        )
        .timeout(const Duration(seconds: 12));
    return _decodeList(response).map(Cotizacion.fromApi).toList();
  }

  Future<Cotizacion> createCotizacion({
    required int requestId,
    required double costoEstimado,
    required double tiempoReparacionHoras,
    required int etaLlegadaMinutos,
    required String descripcion,
    required bool incluyeRepuestos,
    required int garantiaDias,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/cotizaciones/solicitudes/$requestId'),
          headers: _headers(json: true),
          body: jsonEncode({
            'costo_estimado': costoEstimado,
            'tiempo_reparacion_horas': tiempoReparacionHoras,
            'eta_llegada_minutos': etaLlegadaMinutos,
            'descripcion': descripcion.trim(),
            'incluye_repuestos': incluyeRepuestos,
            'garantia_dias': garantiaDias,
          }),
        )
        .timeout(const Duration(seconds: 12));
    return Cotizacion.fromApi(_decodeObject(response));
  }

  Future<Cotizacion> selectCotizacion(int cotizacionId) async {
    final response = await http
        .post(
          _uri('/api/v1/cotizaciones/$cotizacionId/seleccionar'),
          headers: _headers(json: true),
        )
        .timeout(const Duration(seconds: 12));
    return Cotizacion.fromApi(_decodeObject(response));
  }

  Future<void> sendTrackingPing({
    required int requestId,
    required double latitud,
    required double longitud,
    double? velocidadKmh,
    double? rumboGrados,
  }) async {
    final response = await http
        .post(
          _uri('/api/v1/tracking/solicitudes/$requestId/ping'),
          headers: _headers(json: true),
          body: jsonEncode({
            'latitud': latitud,
            'longitud': longitud,
            if (velocidadKmh != null) 'velocidad_kmh': velocidadKmh,
            if (rumboGrados != null) 'rumbo_grados': rumboGrados,
          }),
        )
        .timeout(const Duration(seconds: 12));
    _decodeObject(response);
  }

  Map<String, dynamic> _decodeObject(http.Response response) {
    final body = utf8.decode(response.bodyBytes);
    final json = _decodeJson(body);
    if (response.statusCode >= 400) {
      throw ApiException(_readDetail(json));
    }
    if (json is! Map<String, dynamic>) {
      throw ApiException('El servicio devolvio una respuesta inesperada.');
    }
    return json;
  }

  Future<Map<String, dynamic>> _decodeObjectFromStream(
    http.StreamedResponse response,
  ) async {
    final body = await response.stream.bytesToString();
    final json = _decodeJson(body);
    if (response.statusCode >= 400) {
      throw ApiException(_readDetail(json));
    }
    if (json is! Map<String, dynamic>) {
      throw ApiException('El servicio devolvio una respuesta inesperada.');
    }
    return json;
  }

  List<Map<String, dynamic>> _decodeList(http.Response response) {
    final body = utf8.decode(response.bodyBytes);
    final json = _decodeJson(body);
    if (response.statusCode >= 400) {
      throw ApiException(_readDetail(json));
    }
    if (json is! List<dynamic>) {
      throw ApiException('El servicio devolvio una respuesta inesperada.');
    }
    return json.map((item) => item as Map<String, dynamic>).toList();
  }

  Object? _decodeJson(String body) {
    try {
      return body.trim().isEmpty ? null : jsonDecode(body);
    } on FormatException {
      throw ApiException(
        'El servicio no devolvio JSON valido. Revisa que la API este levantada en $_baseUrl.',
      );
    }
  }

  String _readDetail(Object? payload) {
    if (payload is Map<String, dynamic> && payload['detail'] != null) {
      return payload['detail'].toString();
    }
    return 'No se pudo completar la solicitud al servicio.';
  }
}

class ApiException implements Exception {
  ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

String normalizeBaseUrl(String value) {
  return AppConfig.normalizeBaseUrl(value);
}

String platformDefaultBaseUrl() {
  return AppConfig.defaultBaseUrl;
}
