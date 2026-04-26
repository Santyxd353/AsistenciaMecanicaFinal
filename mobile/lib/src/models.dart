class AppUser {
  const AppUser({
    required this.id,
    required this.username,
    required this.email,
    this.fullName,
    required this.role,
    required this.isActive,
  });

  final int id;
  final String username;
  final String email;
  final String? fullName;
  final String role;
  final bool isActive;

  bool get isDriver => role == 'driver';
  bool get isWorkshopLike => role == 'workshop' || role == 'admin';
  String get displayName =>
      (fullName?.trim().isNotEmpty ?? false) ? fullName!.trim() : username;

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'full_name': fullName,
      'role': role,
      'is_active': isActive,
    };
  }

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      email: json['email'] as String? ?? '',
      fullName: json['full_name'] as String?,
      role: json['role'] as String? ?? 'driver',
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}

class AuthPayload {
  const AuthPayload({
    required this.accessToken,
    required this.tokenType,
    required this.role,
    required this.user,
  });

  final String accessToken;
  final String tokenType;
  final String role;
  final AppUser user;

  factory AuthPayload.fromJson(Map<String, dynamic> json) {
    return AuthPayload(
      accessToken: json['access_token'] as String? ?? '',
      tokenType: json['token_type'] as String? ?? 'bearer',
      role: json['role'] as String? ?? 'driver',
      user: AppUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}

class Vehicle {
  const Vehicle({
    required this.localId,
    this.remoteId,
    required this.placa,
    required this.marca,
    required this.modelo,
    this.color = '',
  });

  final String localId;
  final int? remoteId;
  final String placa;
  final String marca;
  final String modelo;
  final String color;

  String get label {
    final colorPart = color.trim().isEmpty ? '' : ' - $color';
    return '$placa - $marca $modelo$colorPart';
  }

  Vehicle copyWith({
    String? localId,
    int? remoteId,
    String? placa,
    String? marca,
    String? modelo,
    String? color,
  }) {
    return Vehicle(
      localId: localId ?? this.localId,
      remoteId: remoteId ?? this.remoteId,
      placa: placa ?? this.placa,
      marca: marca ?? this.marca,
      modelo: modelo ?? this.modelo,
      color: color ?? this.color,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'local_id': localId,
      'remote_id': remoteId,
      'placa': placa,
      'marca': marca,
      'modelo': modelo,
      'color': color,
    };
  }

  factory Vehicle.fromJson(Map<String, dynamic> json) {
    return Vehicle(
      localId: json['local_id'] as String? ?? '',
      remoteId: json['remote_id'] as int?,
      placa: json['placa'] as String? ?? '',
      marca: json['marca'] as String? ?? '',
      modelo: json['modelo'] as String? ?? '',
      color: json['color'] as String? ?? '',
    );
  }

  factory Vehicle.fromApi(
    Map<String, dynamic> json, {
    required String localId,
  }) {
    return Vehicle(
      localId: localId,
      remoteId: json['id'] as int?,
      placa: json['placa'] as String? ?? '',
      marca: json['marca'] as String? ?? '',
      modelo: json['modelo'] as String? ?? '',
      color: json['color'] as String? ?? '',
    );
  }
}

class Technician {
  const Technician({
    required this.id,
    required this.nombre,
    required this.especialidad,
    required this.disponible,
    this.tallerId,
  });

  final int id;
  final String nombre;
  final String especialidad;
  final bool disponible;
  final int? tallerId;

  String get label => '$nombre - $especialidad';

  Technician copyWith({
    int? id,
    String? nombre,
    String? especialidad,
    bool? disponible,
    int? tallerId,
  }) {
    return Technician(
      id: id ?? this.id,
      nombre: nombre ?? this.nombre,
      especialidad: especialidad ?? this.especialidad,
      disponible: disponible ?? this.disponible,
      tallerId: tallerId ?? this.tallerId,
    );
  }

  factory Technician.fromApi(Map<String, dynamic> json) {
    return Technician(
      id: json['id'] as int,
      nombre: json['nombre'] as String? ?? 'Tecnico',
      especialidad: json['especialidad'] as String? ?? 'General',
      disponible: json['disponible'] as bool? ?? false,
      tallerId: json['taller_id'] as int?,
    );
  }
}

class WorkshopProfile {
  const WorkshopProfile({
    required this.id,
    required this.nombreComercial,
    required this.direccion,
    required this.telefono,
    required this.horarioAtencion,
    required this.especialidades,
    this.emailContacto,
    this.descripcion,
    this.sitioWeb,
    this.latitud,
    this.longitud,
    this.calificacionPromedio = 0,
    this.totalServiciosCompletados = 0,
    this.tiempoRespuestaPromedio,
    this.notificacionesNuevasAsignaciones = true,
    this.notificacionesPush = true,
    this.notificacionesRecordatorios = true,
    this.notificacionesPagos = true,
    this.reportesSemanales = false,
  });

  final int id;
  final String nombreComercial;
  final String direccion;
  final String telefono;
  final String horarioAtencion;
  final String especialidades;
  final String? emailContacto;
  final String? descripcion;
  final String? sitioWeb;
  final double? latitud;
  final double? longitud;
  final double calificacionPromedio;
  final int totalServiciosCompletados;
  final int? tiempoRespuestaPromedio;
  final bool notificacionesNuevasAsignaciones;
  final bool notificacionesPush;
  final bool notificacionesRecordatorios;
  final bool notificacionesPagos;
  final bool reportesSemanales;

  List<String> get specialtyTags => especialidades
      .split(',')
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList();

  factory WorkshopProfile.fromApi(Map<String, dynamic> json) {
    double readDouble(dynamic value) {
      if (value is int) {
        return value.toDouble();
      }
      if (value is double) {
        return value;
      }
      return double.tryParse(value?.toString() ?? '') ?? 0;
    }

    return WorkshopProfile(
      id: json['id'] as int,
      nombreComercial: json['nombre_comercial'] as String? ?? '',
      direccion: json['direccion'] as String? ?? '',
      telefono: json['telefono'] as String? ?? '',
      horarioAtencion: json['horario_atencion'] as String? ?? '',
      especialidades: json['especialidades'] as String? ?? '',
      emailContacto: json['email_contacto'] as String?,
      descripcion: json['descripcion'] as String?,
      sitioWeb: json['sitio_web'] as String?,
      latitud: json['latitud'] == null ? null : readDouble(json['latitud']),
      longitud: json['longitud'] == null ? null : readDouble(json['longitud']),
      calificacionPromedio: readDouble(json['calificacion_promedio']),
      totalServiciosCompletados:
          json['total_servicios_completados'] as int? ?? 0,
      tiempoRespuestaPromedio: json['tiempo_respuesta_promedio'] as int?,
      notificacionesNuevasAsignaciones:
          json['notificaciones_nuevas_asignaciones'] as bool? ?? true,
      notificacionesPush: json['notificaciones_push'] as bool? ?? true,
      notificacionesRecordatorios:
          json['notificaciones_recordatorios'] as bool? ?? true,
      notificacionesPagos: json['notificaciones_pagos'] as bool? ?? true,
      reportesSemanales: json['reportes_semanales'] as bool? ?? false,
    );
  }
}

class WorkshopStats {
  const WorkshopStats({
    required this.workshopId,
    required this.workshopName,
    required this.workshopRating,
    required this.workshopCompletedServices,
    required this.totalCompleted,
    required this.averageIncome,
    required this.totalCommissions,
    required this.totalTechnicians,
    required this.availableTechnicians,
    this.averageResponseMinutes,
  });

  final int workshopId;
  final String workshopName;
  final double workshopRating;
  final int workshopCompletedServices;
  final int totalCompleted;
  final double averageIncome;
  final double totalCommissions;
  final int totalTechnicians;
  final int availableTechnicians;
  final int? averageResponseMinutes;

  factory WorkshopStats.fromApi(Map<String, dynamic> json) {
    double readDouble(dynamic value) {
      if (value is int) {
        return value.toDouble();
      }
      if (value is double) {
        return value;
      }
      return double.tryParse(value?.toString() ?? '') ?? 0;
    }

    final workshopInfo =
        json['taller_info'] as Map<String, dynamic>? ?? const {};
    final services = json['servicios'] as Map<String, dynamic>? ?? const {};
    final technicians = json['tecnicos'] as Map<String, dynamic>? ?? const {};

    return WorkshopStats(
      workshopId: workshopInfo['id'] as int? ?? 0,
      workshopName: workshopInfo['nombre_comercial'] as String? ?? 'Taller',
      workshopRating: readDouble(workshopInfo['calificacion_promedio']),
      workshopCompletedServices:
          workshopInfo['total_servicios_completados'] as int? ?? 0,
      totalCompleted: services['total_completados'] as int? ?? 0,
      averageIncome: readDouble(services['ingreso_promedio_por_servicio']),
      totalCommissions: readDouble(services['comisiones_totales_pagadas']),
      totalTechnicians: technicians['total_tecnicos'] as int? ?? 0,
      availableTechnicians: technicians['tecnicos_disponibles'] as int? ?? 0,
      averageResponseMinutes: json['tiempo_respuesta_promedio'] as int?,
    );
  }
}

class EmergencyRequest {
  const EmergencyRequest({
    required this.id,
    required this.descripcion,
    required this.latitud,
    required this.longitud,
    required this.estado,
    required this.fechaCreacion,
    this.vehiculoId,
    this.tallerId,
    this.tecnicoId,
    this.precioCobrado,
    this.comisionPlataforma,
    this.clasificacionIa,
    this.prioridadIa,
    this.resumenIa,
    this.tallerNombre,
    this.tecnicoNombre,
    this.tecnicoEspecialidad,
  });

  final int id;
  final String descripcion;
  final double latitud;
  final double longitud;
  final String estado;
  final DateTime fechaCreacion;
  final int? vehiculoId;
  final int? tallerId;
  final int? tecnicoId;
  final double? precioCobrado;
  final double? comisionPlataforma;
  final String? clasificacionIa;
  final String? prioridadIa;
  final String? resumenIa;
  final String? tallerNombre;
  final String? tecnicoNombre;
  final String? tecnicoEspecialidad;

  bool get isClosed => estado == 'resuelta' || estado == 'cancelada';
  bool get paymentReady => estado == 'en_progreso' || estado == 'resuelta';
  bool get serviceInProgress => estado == 'asignada' || estado == 'en_progreso';

  String get statusLabel {
    switch (estado) {
      case 'pendiente':
        return 'Pendiente';
      case 'asignada':
        return 'Asignada';
      case 'en_progreso':
        return 'En progreso';
      case 'resuelta':
        return 'Atendida';
      case 'cancelada':
        return 'Cancelada';
      default:
        return estado;
    }
  }

  factory EmergencyRequest.fromApi(Map<String, dynamic> json) {
    double readDouble(String key) {
      final value = json[key];
      if (value is int) {
        return value.toDouble();
      }
      if (value is double) {
        return value;
      }
      return double.parse(value.toString());
    }

    double? readNullableDouble(String key) {
      final value = json[key];
      if (value == null) {
        return null;
      }
      if (value is int) {
        return value.toDouble();
      }
      if (value is double) {
        return value;
      }
      return double.tryParse(value.toString());
    }

    return EmergencyRequest(
      id: json['id'] as int,
      descripcion: json['descripcion'] as String? ?? '',
      latitud: readDouble('latitud'),
      longitud: readDouble('longitud'),
      estado: json['estado'] as String? ?? 'pendiente',
      fechaCreacion: DateTime.parse(json['fecha_creacion'] as String),
      vehiculoId: json['vehiculo_id'] as int?,
      tallerId: json['taller_id'] as int?,
      tecnicoId: json['tecnico_id'] as int?,
      precioCobrado: readNullableDouble('precio_cobrado'),
      comisionPlataforma: readNullableDouble('comision_plataforma'),
      clasificacionIa: json['clasificacion_ia'] as String?,
      prioridadIa: json['prioridad_ia'] as String?,
      resumenIa: json['resumen_ia'] as String?,
      tallerNombre: json['taller_nombre'] as String?,
      tecnicoNombre: json['tecnico_nombre'] as String?,
      tecnicoEspecialidad: json['tecnico_especialidad'] as String?,
    );
  }
}

class LocalRequestMeta {
  const LocalRequestMeta({
    required this.requestId,
    required this.vehicleLabel,
    required this.issueType,
    required this.imagePaths,
    this.audioPath,
    this.extraNotes = '',
  });

  final int requestId;
  final String vehicleLabel;
  final String issueType;
  final List<String> imagePaths;
  final String? audioPath;
  final String extraNotes;

  Map<String, dynamic> toJson() {
    return {
      'request_id': requestId,
      'vehicle_label': vehicleLabel,
      'issue_type': issueType,
      'image_paths': imagePaths,
      'audio_path': audioPath,
      'extra_notes': extraNotes,
    };
  }

  factory LocalRequestMeta.fromJson(Map<String, dynamic> json) {
    return LocalRequestMeta(
      requestId: json['request_id'] as int,
      vehicleLabel: json['vehicle_label'] as String? ?? '',
      issueType: json['issue_type'] as String? ?? '',
      imagePaths: (json['image_paths'] as List<dynamic>? ?? [])
          .map((path) => path.toString())
          .toList(),
      audioPath: json['audio_path'] as String?,
      extraNotes: json['extra_notes'] as String? ?? '',
    );
  }
}

class AppSnapshot {
  const AppSnapshot({
    required this.baseUrl,
    required this.accessToken,
    required this.currentUser,
    required this.vehicles,
    required this.requestMetas,
  });

  final String baseUrl;
  final String? accessToken;
  final AppUser? currentUser;
  final List<Vehicle> vehicles;
  final List<LocalRequestMeta> requestMetas;
}
