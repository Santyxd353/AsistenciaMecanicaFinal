import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../repositories.dart';
import 'local_db.dart';

/// Cola offline de emergencias.
///
/// Flujo:
/// 1. `enqueue` guarda la emergencia en SQLite con un `cliente_sync_id` UUID.
/// 2. Cuando hay conexión, `flush` recorre las pendientes y las POSTea al
///    backend reutilizando el dedup por `cliente_sync_id` (ya implementado
///    en backend/app/api/solicitudes.py).
/// 3. Los resultados se emiten por `events$` para que la UI refresque
///    estado (enviada/pendiente/error).
class OfflineQueueService {
  OfflineQueueService(this._apiBuilder);

  /// El caller pasa un builder que devuelve el ApiClient autenticado
  /// vigente (token actual). Así la cola siempre usa la sesión correcta.
  final ApiClient Function() _apiBuilder;

  final _uuid = const Uuid();
  final _events = StreamController<OfflineFlushResult>.broadcast();

  Stream<OfflineFlushResult> get events$ => _events.stream;

  Future<String> enqueue(Map<String, dynamic> payload) async {
    if (kIsWeb) {
      return _uuid.v4();
    }
    final db = await LocalDb.instance.db;
    final syncId = _uuid.v4();
    final fullPayload = {...payload, 'cliente_sync_id': syncId};
    await db.insert('pending_emergencias', {
      'cliente_sync_id': syncId,
      'payload': jsonEncode(fullPayload),
      'status': 'pending',
      'attempts': 0,
      'created_at': DateTime.now().millisecondsSinceEpoch,
    });
    return syncId;
  }

  Future<List<OfflineEmergency>> visibleEmergencies() async {
    if (kIsWeb) {
      return const [];
    }
    final db = await LocalDb.instance.db;
    final rows = await db.query(
      'pending_emergencias',
      where: 'status != ?',
      whereArgs: ['synced'],
      orderBy: 'created_at DESC',
    );
    return rows.map(OfflineEmergency.fromRow).toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> pending() async {
    if (kIsWeb) {
      return const [];
    }
    final db = await LocalDb.instance.db;
    return db.query(
      'pending_emergencias',
      where: 'status IN (?, ?, ?)',
      whereArgs: ['pending', 'error', 'syncing'],
      orderBy: 'created_at ASC',
    );
  }

  Future<int> pendingCount() async {
    if (kIsWeb) {
      return 0;
    }
    final db = await LocalDb.instance.db;
    final rows = await db.rawQuery(
      "SELECT COUNT(*) AS c FROM pending_emergencias WHERE status IN ('pending', 'error', 'syncing')",
    );
    return (rows.first['c'] as int?) ?? 0;
  }

  /// Sincroniza todas las pendientes contra el backend.
  /// Backend dedupea por `cliente_sync_id`, así que un POST repetido es seguro.
  Future<OfflineFlushResult> flush() async {
    if (kIsWeb) {
      final result = OfflineFlushResult(synced: 0, pending: 0, failed: 0);
      _events.add(result);
      return result;
    }
    final db = await LocalDb.instance.db;
    final rows = await pending();
    int synced = 0;
    int failed = 0;
    String? lastError;

    for (final row in rows) {
      final id = row['id'] as int;
      final payload =
          jsonDecode(row['payload'] as String) as Map<String, dynamic>;
      try {
        await db.update(
          'pending_emergencias',
          {'status': 'syncing', 'last_error': null},
          where: 'id = ?',
          whereArgs: [id],
        );
        await _apiBuilder().createRequestRaw(payload);
        await db.update(
          'pending_emergencias',
          {'status': 'synced'},
          where: 'id = ?',
          whereArgs: [id],
        );
        synced++;
      } catch (e) {
        failed++;
        lastError = e.toString();
        await db.update(
          'pending_emergencias',
          {
            'status': 'error',
            'attempts': (row['attempts'] as int) + 1,
            'last_error': lastError,
          },
          where: 'id = ?',
          whereArgs: [id],
        );
      }
    }

    final remaining = await pendingCount();
    final result = OfflineFlushResult(
      synced: synced,
      pending: remaining,
      failed: failed,
      lastError: lastError,
    );
    _events.add(result);
    return result;
  }

  void dispose() {
    _events.close();
  }
}

class OfflineEmergency {
  const OfflineEmergency({
    required this.id,
    required this.syncId,
    required this.payload,
    required this.status,
    required this.attempts,
    required this.createdAt,
    this.lastError,
  });

  final int id;
  final String syncId;
  final Map<String, dynamic> payload;
  final String status;
  final int attempts;
  final DateTime createdAt;
  final String? lastError;

  bool get isError => status == 'error';
  bool get isSyncing => status == 'syncing';
  bool get isPending => status == 'pending';

  String get title {
    final raw = (payload['descripcion'] ?? '').toString();
    if (raw.trim().isEmpty) {
      return 'Emergencia pendiente';
    }
    return raw.trim();
  }

  double? get latitud => _readDouble(payload['latitud']);
  double? get longitud => _readDouble(payload['longitud']);
  int? get vehiculoId => payload['vehiculo_id'] is int
      ? payload['vehiculo_id'] as int
      : int.tryParse(payload['vehiculo_id']?.toString() ?? '');

  static OfflineEmergency fromRow(Map<String, dynamic> row) {
    final payload =
        jsonDecode(row['payload'] as String) as Map<String, dynamic>;
    return OfflineEmergency(
      id: row['id'] as int,
      syncId: row['cliente_sync_id'] as String,
      payload: payload,
      status: row['status'] as String,
      attempts: row['attempts'] as int? ?? 0,
      createdAt: DateTime.fromMillisecondsSinceEpoch(row['created_at'] as int),
      lastError: row['last_error'] as String?,
    );
  }

  static double? _readDouble(dynamic value) {
    if (value is int) return value.toDouble();
    if (value is double) return value;
    return double.tryParse(value?.toString() ?? '');
  }
}

class OfflineFlushResult {
  OfflineFlushResult({
    required this.synced,
    required this.pending,
    required this.failed,
    this.lastError,
  });

  final int synced;
  final int pending;
  final int failed;
  final String? lastError;
}
