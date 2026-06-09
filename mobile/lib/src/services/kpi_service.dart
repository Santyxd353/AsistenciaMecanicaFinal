import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../repositories.dart';

/// Servicio para consumir los KPIs operacionales del backend
/// (GET /api/v1/kpis). Backend ya filtra por tenant via JWT, así que
/// los números devueltos corresponden al tenant del usuario logueado.
///
/// Parser tolerante: backend puede devolver un mismo KPI en distintas formas
/// según el momento (campos `*_min` o sin sufijo, campos primitivos vs
/// objetos {total, porcentaje}). Lo resolvemos vía `_num()` y `_int()` que
/// aceptan num/string/null sin lanzar `_TypeError`.
class KpiService {
  KpiService(this._apiBuilder);
  final ApiClient Function() _apiBuilder;

  Future<KpiBundle> fetchAll({int? days}) async {
    final api = _apiBuilder();
    final url = api.buildUri('/api/v1/kpis/${days != null ? '?days=$days' : ''}');
    final resp = await http
        .get(url, headers: api.authHeaders())
        .timeout(const Duration(seconds: 15));
    if (resp.statusCode >= 400) {
      throw Exception('KPIs HTTP ${resp.statusCode}: ${resp.body}');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return KpiBundle.fromJson(data);
  }

  Future<WorkshopReportsBundle> fetchWorkshopReports({int days = 30}) async {
    final api = _apiBuilder();
    final url = api.buildUri('/api/v1/kpis/taller?dias=$days');
    final resp = await http
        .get(url, headers: api.authHeaders())
        .timeout(const Duration(seconds: 15));
    if (resp.statusCode >= 400) {
      throw Exception('Reportes HTTP ${resp.statusCode}: ${resp.body}');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return WorkshopReportsBundle.fromJson(data);
  }
}

double? _num(dynamic raw) {
  if (raw == null) return null;
  if (raw is num) return raw.toDouble();
  if (raw is String) return double.tryParse(raw);
  return null;
}

int _int(dynamic raw, {int fallback = 0}) {
  if (raw == null) return fallback;
  if (raw is num) return raw.toInt();
  if (raw is String) return int.tryParse(raw) ?? fallback;
  return fallback;
}

/// Backend devuelve casos cancelados como `{total: N, porcentaje: %}`. Si en
/// el futuro vuelve a ser un número plano lo absorbemos también.
int _casosCancelados(dynamic raw) {
  if (raw is num) return raw.toInt();
  if (raw is Map) return _int(raw['total']);
  return 0;
}

class KpiBundle {
  KpiBundle({
    required this.assignmentAvgMin,
    required this.arrivalAvgMin,
    required this.slaPercentage,
    required this.canceladosCount,
    required this.incidentesPorTipo,
    required this.topTalleres,
    required this.zonas,
  });

  final double? assignmentAvgMin;
  final double? arrivalAvgMin;
  final double? slaPercentage;
  final int canceladosCount;
  final Map<String, int> incidentesPorTipo;
  final List<KpiTaller> topTalleres;
  final List<KpiZona> zonas;

  factory KpiBundle.fromJson(Map<String, dynamic> j) {
    return KpiBundle(
      // Backend canonical: `*_min` y `*_pct`. Aceptamos también la forma
      // legacy sin sufijo por si algún cliente quedó con la versión vieja.
      assignmentAvgMin: _num(j['tiempo_promedio_asignacion_min']) ??
          _num(j['tiempo_promedio_asignacion']),
      arrivalAvgMin: _num(j['tiempo_promedio_llegada_min']) ??
          _num(j['tiempo_promedio_llegada']),
      slaPercentage: _num(j['sla_cumplimiento_pct']) ??
          _num(j['cumplimiento_sla']),
      canceladosCount: _casosCancelados(j['casos_cancelados']),
      incidentesPorTipo: ((j['incidentes_por_tipo'] as Map?) ?? const {}).map(
        (k, v) => MapEntry(k.toString(), _int(v)),
      ),
      topTalleres: ((j['talleres_mas_eficientes'] as List?) ??
              (j['talleres_eficientes'] as List?) ??
              const [])
          .whereType<Map>()
          .map((e) => KpiTaller.fromJson(e.cast<String, dynamic>()))
          .toList(),
      zonas: ((j['zonas_con_mas_incidentes'] as List?) ??
              (j['zonas_incidentes'] as List?) ??
              const [])
          .whereType<Map>()
          .map((e) => KpiZona.fromJson(e.cast<String, dynamic>()))
          .toList(),
    );
  }
}

class KpiTaller {
  KpiTaller({required this.nombre, required this.score, required this.servicios});
  final String nombre;
  final double score;
  final int servicios;
  factory KpiTaller.fromJson(Map<String, dynamic> j) => KpiTaller(
        nombre: (j['nombre'] ?? j['taller_nombre'] ?? '?').toString(),
        // Backend canonical: `score_eficiencia` + `finalizados`.
        score: _num(j['score_eficiencia']) ?? _num(j['score']) ?? 0,
        servicios: _int(j['finalizados']) > 0
            ? _int(j['finalizados'])
            : _int(j['servicios_finalizados']),
      );
}

class KpiZona {
  KpiZona({required this.lat, required this.lng, required this.count});
  final double lat;
  final double lng;
  final int count;
  factory KpiZona.fromJson(Map<String, dynamic> j) => KpiZona(
        // Backend canonical: `lat`, `lng`, `incidentes`.
        lat: _num(j['lat']) ?? _num(j['latitud']) ?? 0,
        lng: _num(j['lng']) ?? _num(j['longitud']) ?? 0,
        count: _int(j['incidentes']) > 0
            ? _int(j['incidentes'])
            : _int(j['cantidad']),
      );
}

String _text(dynamic raw, {String fallback = 'Sin dato'}) {
  final value = raw?.toString().trim() ?? '';
  return value.isEmpty ? fallback : value;
}

class WorkshopReportsBundle {
  WorkshopReportsBundle({
    required this.tallerNombre,
    required this.ventanaDias,
    required this.resumen,
    required this.trabajadores,
    required this.tiposIncidente,
    required this.modelosAuxiliados,
    required this.marcasAuxiliadas,
    required this.zonas,
    required this.estados,
  });

  final String tallerNombre;
  final int ventanaDias;
  final WorkshopReportSummary resumen;
  final List<WorkerReportItem> trabajadores;
  final List<ReportCountItem> tiposIncidente;
  final List<ReportCountItem> modelosAuxiliados;
  final List<ReportCountItem> marcasAuxiliadas;
  final List<ReportZoneItem> zonas;
  final List<ReportCountItem> estados;

  factory WorkshopReportsBundle.fromJson(Map<String, dynamic> j) {
    final taller = (j['taller'] as Map?)?.cast<String, dynamic>() ?? const {};
    return WorkshopReportsBundle(
      tallerNombre: _text(taller['nombre'], fallback: 'Mi taller'),
      ventanaDias: _int(j['ventana_dias'], fallback: 30),
      resumen: WorkshopReportSummary.fromJson(
        ((j['resumen'] as Map?) ?? const {}).cast<String, dynamic>(),
      ),
      trabajadores: _list(j['trabajadores_mas_rendimiento'])
          .map(WorkerReportItem.fromJson)
          .toList(),
      tiposIncidente: _list(j['tipos_incidente'])
          .map(ReportCountItem.fromJson)
          .toList(),
      modelosAuxiliados: _list(j['modelos_auxiliados'])
          .map(ReportCountItem.fromJson)
          .toList(),
      marcasAuxiliadas: _list(j['marcas_auxiliadas'])
          .map(ReportCountItem.fromJson)
          .toList(),
      zonas: _list(j['zonas_mas_auxilio']).map(ReportZoneItem.fromJson).toList(),
      estados: _list(j['estados']).map(ReportCountItem.fromJson).toList(),
    );
  }
}

List<Map<String, dynamic>> _list(dynamic raw) {
  return ((raw as List?) ?? const [])
      .whereType<Map>()
      .map((item) => item.cast<String, dynamic>())
      .toList();
}

class WorkshopReportSummary {
  WorkshopReportSummary({
    required this.solicitudes,
    required this.pendientes,
    required this.activas,
    required this.finalizadas,
    required this.canceladas,
    required this.ingresos,
    required this.neto,
    required this.tiempoLlegadaMin,
    required this.tiempoCierreMin,
  });

  final int solicitudes;
  final int pendientes;
  final int activas;
  final int finalizadas;
  final int canceladas;
  final double ingresos;
  final double neto;
  final double? tiempoLlegadaMin;
  final double? tiempoCierreMin;

  factory WorkshopReportSummary.fromJson(Map<String, dynamic> j) {
    return WorkshopReportSummary(
      solicitudes: _int(j['solicitudes']),
      pendientes: _int(j['pendientes']),
      activas: _int(j['activas']),
      finalizadas: _int(j['finalizadas']),
      canceladas: _int(j['canceladas']),
      ingresos: _num(j['ingresos']) ?? 0,
      neto: _num(j['neto']) ?? 0,
      tiempoLlegadaMin: _num(j['tiempo_promedio_llegada_min']),
      tiempoCierreMin: _num(j['tiempo_promedio_cierre_min']),
    );
  }
}

class WorkerReportItem {
  WorkerReportItem({
    required this.nombre,
    required this.total,
    required this.finalizados,
    required this.activos,
    required this.cancelados,
    required this.ingresos,
    required this.tasaFinalizacion,
    required this.score,
    required this.calificacion,
    required this.tiempoCierreMin,
  });

  final String nombre;
  final int total;
  final int finalizados;
  final int activos;
  final int cancelados;
  final double ingresos;
  final double tasaFinalizacion;
  final double score;
  final double calificacion;
  final double? tiempoCierreMin;

  factory WorkerReportItem.fromJson(Map<String, dynamic> j) {
    return WorkerReportItem(
      nombre: _text(j['nombre'], fallback: 'Mecanico'),
      total: _int(j['total']),
      finalizados: _int(j['finalizados']),
      activos: _int(j['activos']),
      cancelados: _int(j['cancelados']),
      ingresos: _num(j['ingresos']) ?? 0,
      tasaFinalizacion: _num(j['tasa_finalizacion_pct']) ?? 0,
      score: _num(j['score']) ?? 0,
      calificacion: _num(j['calificacion']) ?? 0,
      tiempoCierreMin: _num(j['tiempo_promedio_cierre_min']),
    );
  }
}

class ReportCountItem {
  ReportCountItem({required this.nombre, required this.total});

  final String nombre;
  final int total;

  factory ReportCountItem.fromJson(Map<String, dynamic> j) {
    return ReportCountItem(
      nombre: _text(j['nombre']),
      total: _int(j['total']),
    );
  }
}

class ReportZoneItem {
  ReportZoneItem({required this.lat, required this.lng, required this.total});

  final double lat;
  final double lng;
  final int total;

  factory ReportZoneItem.fromJson(Map<String, dynamic> j) {
    return ReportZoneItem(
      lat: _num(j['lat']) ?? 0,
      lng: _num(j['lng']) ?? 0,
      total: _int(j['total']),
    );
  }
}
