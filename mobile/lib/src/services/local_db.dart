import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// SQLite local para offline.
/// Tabla `pending_emergencias`: encola las solicitudes creadas sin internet
/// para sincronizarlas cuando vuelva la conexión.
class LocalDb {
  LocalDb._();
  static final LocalDb instance = LocalDb._();

  Database? _db;

  Future<Database> get db async {
    if (_db != null) return _db!;
    final dir = await getDatabasesPath();
    final path = p.join(dir, 'asistencia_mecanica.db');
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE pending_emergencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_sync_id TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            last_error TEXT
          )
        ''');
        await db.execute(
          'CREATE INDEX idx_pending_status ON pending_emergencias(status)',
        );
      },
    );
    return _db!;
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
