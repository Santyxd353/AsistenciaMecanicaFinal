import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

class RouteService {
  RouteService._();

  static final Map<String, List<LatLng>> _cache = {};

  static Future<List<LatLng>> drivingRoute({
    required LatLng origin,
    required LatLng destination,
  }) async {
    final key = [
      origin.latitude.toStringAsFixed(5),
      origin.longitude.toStringAsFixed(5),
      destination.latitude.toStringAsFixed(5),
      destination.longitude.toStringAsFixed(5),
    ].join('|');

    final cached = _cache[key];
    if (cached != null) {
      return cached;
    }

    final uri = Uri.parse(
      'https://router.project-osrm.org/route/v1/driving/'
      '${origin.longitude},${origin.latitude};'
      '${destination.longitude},${destination.latitude}'
      '?overview=full&geometries=geojson',
    );

    try {
      final response = await http.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) {
        return [origin, destination];
      }
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final routes = body['routes'] as List<dynamic>?;
      if (routes == null || routes.isEmpty) {
        return [origin, destination];
      }
      final geometry = routes.first['geometry'] as Map<String, dynamic>?;
      final coordinates = geometry?['coordinates'] as List<dynamic>?;
      if (coordinates == null || coordinates.length < 2) {
        return [origin, destination];
      }
      final points = coordinates
          .whereType<List<dynamic>>()
          .map(
            (item) => LatLng(
              (item[1] as num).toDouble(),
              (item[0] as num).toDouble(),
            ),
          )
          .toList(growable: false);
      final route = points.length >= 2 ? points : [origin, destination];
      _cache[key] = route;
      return route;
    } catch (_) {
      return [origin, destination];
    }
  }
}
