import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class LocalRepository {
  LocalRepository(this._prefs);

  static const _baseUrlKey = 'base_url';
  static const _tokenKey = 'access_token';
  static const _userKey = 'current_user';
  static const _vehiclesKey = 'vehicles';
  static const _requestMetasKey = 'request_metas';
  static const defaultBaseUrl = 'http://10.0.2.2:8000';

  final SharedPreferences _prefs;

  AppSnapshot load() {
    final userRaw = _prefs.getString(_userKey);
    final vehiclesRaw = _prefs.getString(_vehiclesKey);
    final requestsRaw = _prefs.getString(_requestMetasKey);

    final user = userRaw == null ? null : AppUser.fromJson(jsonDecode(userRaw) as Map<String, dynamic>);
    final vehicles = vehiclesRaw == null
        ? <Vehicle>[]
        : (jsonDecode(vehiclesRaw) as List<dynamic>)
            .map((item) => Vehicle.fromJson(item as Map<String, dynamic>))
            .toList();
    final requestMetas = requestsRaw == null
        ? <LocalRequestMeta>[]
        : (jsonDecode(requestsRaw) as List<dynamic>)
            .map((item) => LocalRequestMeta.fromJson(item as Map<String, dynamic>))
            .toList();

    return AppSnapshot(
      baseUrl: normalizeBaseUrl(_prefs.getString(_baseUrlKey) ?? defaultBaseUrl),
      accessToken: _prefs.getString(_tokenKey),
      currentUser: user,
      vehicles: vehicles,
      requestMetas: requestMetas,
    );
  }

  Future<void> saveBaseUrl(String value) async {
    await _prefs.setString(_baseUrlKey, normalizeBaseUrl(value));
  }

  Future<void> saveSession({required String token, required AppUser user}) async {
    await _prefs.setString(_tokenKey, token);
    await _prefs.setString(_userKey, jsonEncode(user.toJson()));
  }

  Future<void> clearSession() async {
    await _prefs.remove(_tokenKey);
    await _prefs.remove(_userKey);
    await _prefs.remove(_vehiclesKey);
    await _prefs.remove(_requestMetasKey);
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
}

class ApiClient {
  ApiClient({required String baseUrl, this.token}) : _baseUrl = normalizeBaseUrl(baseUrl);

  final String _baseUrl;
  final String? token;

  Uri _uri(String path) => Uri.parse('$_baseUrl$path');

  Map<String, String> _headers({bool json = false}) {
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null && token!.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> ping() async {
    final response = await http.get(_uri('/')).timeout(const Duration(seconds: 8));
    return _decodeObject(response);
  }

  Future<AuthPayload> login({
    required String username,
    required String password,
  }) async {
    final response = await http.post(
      _uri('/api/v1/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'username=${Uri.encodeQueryComponent(username)}&password=${Uri.encodeQueryComponent(password)}',
    ).timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AuthPayload> register({
    required String path,
    required String username,
    required String email,
    required String fullName,
    required String password,
  }) async {
    final response = await http.post(
      _uri(path),
      headers: _headers(json: true),
      body: jsonEncode({
        'username': username,
        'email': email,
        'full_name': fullName,
        'password': password,
      }),
    ).timeout(const Duration(seconds: 12));
    return AuthPayload.fromJson(_decodeObject(response));
  }

  Future<AppUser> getMe() async {
    final response = await http.get(_uri('/api/v1/auth/me'), headers: _headers()).timeout(const Duration(seconds: 12));
    return AppUser.fromJson(_decodeObject(response));
  }

  Future<AppUser> updateMe({
    required String username,
    required String email,
    required String fullName,
  }) async {
    final response = await http.put(
      _uri('/api/v1/auth/me'),
      headers: _headers(json: true),
      body: jsonEncode({
        'username': username,
        'email': email,
        'full_name': fullName,
      }),
    ).timeout(const Duration(seconds: 12));
    return AppUser.fromJson(_decodeObject(response));
  }

  Future<List<Vehicle>> fetchVehicles(List<Vehicle> localVehicles) async {
    final response = await http.get(_uri('/api/v1/vehiculos/'), headers: _headers()).timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    final localIdsByRemote = {
      for (final vehicle in localVehicles)
        if (vehicle.remoteId != null) vehicle.remoteId!: vehicle.localId,
    };

    return payload.map((item) {
      final id = item['id'] as int?;
      final fallbackLocalId = 'vehicle-${id ?? DateTime.now().millisecondsSinceEpoch}';
      return Vehicle.fromApi(
        item,
        localId: id == null ? fallbackLocalId : (localIdsByRemote[id] ?? fallbackLocalId),
      );
    }).toList();
  }

  Future<Vehicle> createVehicle(Vehicle vehicle) async {
    final response = await http.post(
      _uri('/api/v1/vehiculos/'),
      headers: _headers(json: true),
      body: jsonEncode({
        'placa': vehicle.placa,
        'marca': vehicle.marca,
        'modelo': vehicle.modelo,
        'color': vehicle.color,
      }),
    ).timeout(const Duration(seconds: 12));
    return Vehicle.fromApi(_decodeObject(response), localId: vehicle.localId);
  }

  Future<List<EmergencyRequest>> fetchRequests() async {
    final response = await http.get(_uri('/api/v1/solicitudes/'), headers: _headers()).timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(EmergencyRequest.fromApi).toList();
  }

  Future<List<Technician>> fetchTechnicians() async {
    final response = await http.get(_uri('/api/v1/tecnicos/'), headers: _headers()).timeout(const Duration(seconds: 12));
    final payload = _decodeList(response);
    return payload.map(Technician.fromApi).toList();
  }

  Future<EmergencyRequest> createRequest({
    required String descripcion,
    required double latitud,
    required double longitud,
    int? vehiculoId,
  }) async {
    final response = await http.post(
      _uri('/api/v1/solicitudes/'),
      headers: _headers(json: true),
      body: jsonEncode({
        'descripcion': descripcion,
        'latitud': latitud,
        'longitud': longitud,
        'estado': 'pendiente',
        if (vehiculoId != null) 'vehiculo_id': vehiculoId,
      }),
    ).timeout(const Duration(seconds: 12));
    return EmergencyRequest.fromApi(_decodeObject(response));
  }

  Map<String, dynamic> _decodeObject(http.Response response) {
    final json = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 400) {
      throw ApiException(_readDetail(json));
    }
    return json as Map<String, dynamic>;
  }

  List<Map<String, dynamic>> _decodeList(http.Response response) {
    final json = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 400) {
      throw ApiException(_readDetail(json));
    }
    return (json as List<dynamic>).map((item) => item as Map<String, dynamic>).toList();
  }

  String _readDetail(Object? payload) {
    if (payload is Map<String, dynamic> && payload['detail'] != null) {
      return payload['detail'].toString();
    }
    return 'No se pudo completar la solicitud al backend.';
  }
}

class ApiException implements Exception {
  ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

String normalizeBaseUrl(String value) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) {
    return LocalRepository.defaultBaseUrl;
  }
  return trimmed.endsWith('/') ? trimmed.substring(0, trimmed.length - 1) : trimmed;
}
