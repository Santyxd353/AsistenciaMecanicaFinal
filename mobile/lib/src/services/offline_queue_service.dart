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

  Future<List<Map<String, dynamic>>> pending() async {
    if (kIsWeb) {
      return const [];
    }
    final db = await LocalDb.instance.db;
    return db.query(
      'pending_emergencias',
      where: 'status = ?',
      whereArgs: ['pending'],
      orderBy: 'created_at ASC',
    );
  }

  Future<int> pendingCount() async {
    if (kIsWeb) {
      return 0;
    }
    final db = await LocalDb.instance.db;
    final rows = await db.rawQuery(
      "SELECT COUNT(*) AS c FROM pending_emergencias WHERE status='pending'",
    );
    return (rows.first['c'] as int?) ?? 0;
  }

  /// Sincroniza todas las pendientes contra el backend.
  /// Backend dedupea por `cliente_sync_id`, así que un POST repetido es seguro.
  Future<OfflineFlushResult> flush() async {
    if (kIsWeb) {
      final result = OfflineFlushResult(
        synced: 0,
        pending: 0,
        failed: 0,
      );
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
      final payload = jsonDecode(row['payload'] as String) as Map<String, dynamic>;
      try {
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
