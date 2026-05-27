/**
 * Cola de sincronización offline para incidentes creados sin conexión.
 *
 * Persiste en IndexedDB (DB: `mecanica-offline`, store: `incidentes`).
 * Cada entrada lleva:
 *   * `id` interno (uuid v4) → permite distinguir y dedupe local.
 *   * `idempotencyKey` que el backend usa para evitar duplicados si el cliente
 *     reintenta. Se envía como header `X-Idempotency-Key` y `cliente_sync_id`.
 *   * `payload`: el cuerpo exacto que se enviará al endpoint REST.
 *   * `status`: `pending` | `syncing` | `synced` | `error`.
 *   * `attempts`, `lastError`, `createdAt`, `updatedAt` para diagnóstico.
 *
 * `enqueue()` siempre guarda primero en IndexedDB y devuelve el id local.
 * `flush()` recorre las pendientes y POSTea contra el endpoint. Errores 4xx
 * permanentes marcan `error`; errores transitorios (red, 5xx, timeout) dejan
 * la entrada en `pending` para reintentar.
 *
 * El listener `online` del browser invoca `flush()`. El service worker de
 * Angular mantiene shell/assets/API cacheados para que la app abra sin red.
 */

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, Subject, firstValueFrom, from } from 'rxjs';
import { catchError, switchMap, tap } from 'rxjs/operators';

const DB_NAME = 'mecanica-offline';
const DB_VERSION = 1;
const STORE = 'incidentes';

export type SyncStatus = 'pending' | 'syncing' | 'synced' | 'error';

export interface OfflineIncidente {
  id: string;
  idempotencyKey: string;
  endpoint: string;
  payload: unknown;
  status: SyncStatus;
  attempts: number;
  lastError?: string;
  createdAt: number;
  updatedAt: number;
}

function uuid(): string {
  // Versión simple v4 sin dependencia adicional. crypto.randomUUID() existe en
  // todos los browsers modernos pero queda este fallback por compatibilidad.
  return (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
}

@Injectable({ providedIn: 'root' })
export class OfflineQueueService {
  private readonly http = inject(HttpClient);
  private dbPromise: Promise<IDBDatabase> | null = null;
  private readonly queueSubject = new BehaviorSubject<OfflineIncidente[]>([]);
  readonly queue$ = this.queueSubject.asObservable();
  /** Emite tras cada flush completado (auto al volver online, o manual). */
  private readonly flushedSubject = new Subject<{ synced: number; pending: number; failed: number }>();
  readonly flushed$ = this.flushedSubject.asObservable();

  constructor() {
    // Refrescar lista al arrancar y disparar flush automático al volver online.
    this.refresh();
    window.addEventListener('online', () => this.flush().subscribe());
    // Si la app abre ya con conexión y quedaron pendientes de una sesión
    // anterior, el evento `online` no se dispara: forzamos un flush inicial.
    if (navigator.onLine) {
      this.flush().subscribe();
    }
  }

  /** Encola una emergencia para sincronizar después. */
  enqueue(endpoint: string, payload: unknown): Observable<string> {
    const idempotencyKey = uuid();
    const payloadWithSyncId = (
      payload !== null
      && typeof payload === 'object'
      && !Array.isArray(payload)
    )
      ? { ...(payload as Record<string, unknown>), cliente_sync_id: idempotencyKey }
      : payload;
    const item: OfflineIncidente = {
      id: uuid(),
      idempotencyKey,
      endpoint,
      payload: payloadWithSyncId,
      status: 'pending',
      attempts: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    return from(this.openDb()).pipe(
      switchMap((db) => from(this.put(db, item))),
      tap(() => this.refresh()),
      switchMap(() => from(Promise.resolve(item.id))),
    );
  }

  /** Lista todas las entradas (cualquier estado). */
  list(): Observable<OfflineIncidente[]> {
    return from(this.openDb()).pipe(
      switchMap((db) => from(this.getAll(db))),
    );
  }

  /** Reintenta sincronizar las entradas con status `pending` o `error`. */
  flush(): Observable<{ synced: number; pending: number; failed: number }> {
    return from(this.openDb()).pipe(
      switchMap(async (db) => {
        const items = await this.getAll(db);
        const pendientes = items.filter((item) => item.status === 'pending' || item.status === 'error');
        let synced = 0;
        let failed = 0;
        for (const item of pendientes) {
          item.status = 'syncing';
          item.updatedAt = Date.now();
          item.attempts += 1;
          await this.put(db, item);
          try {
            await firstValueFrom(this.http.post(item.endpoint, item.payload, {
              headers: { 'X-Idempotency-Key': item.idempotencyKey },
            }));
            item.status = 'synced';
            synced += 1;
          } catch (err) {
            const httpErr = err as { status?: number; message?: string };
            // 4xx permanente → error definitivo (no reintenta el flush automático).
            if (httpErr.status && httpErr.status >= 400 && httpErr.status < 500) {
              item.status = 'error';
              item.lastError = httpErr.message ?? `HTTP ${httpErr.status}`;
              failed += 1;
            } else {
              item.status = 'pending';
              item.lastError = httpErr.message ?? 'network';
            }
          }
          item.updatedAt = Date.now();
          await this.put(db, item);
        }
        const restante = (await this.getAll(db)).filter((item) => item.status === 'pending').length;
        this.refresh();
        const resultado = { synced, pending: restante, failed };
        this.flushedSubject.next(resultado);
        return resultado;
      }),
      catchError((err) => {
        console.error('[offline-queue] flush falló', err);
        return from(Promise.resolve({ synced: 0, pending: 0, failed: 0 }));
      }),
    );
  }

  /** Elimina las entradas ya sincronizadas (`synced`). Limpia ruido en la UI. */
  purgeSynced(): Observable<number> {
    return from(this.openDb()).pipe(
      switchMap(async (db) => {
        const items = await this.getAll(db);
        const a_borrar = items.filter((item) => item.status === 'synced');
        for (const item of a_borrar) {
          await this.delete(db, item.id);
        }
        this.refresh();
        return a_borrar.length;
      }),
    );
  }

  private refresh(): void {
    this.list().subscribe((items) => this.queueSubject.next(items));
  }

  // ----------------------------------------------------------------------
  // IndexedDB helpers (Promise-based wrappers para evitar arrastrar idb-lib).

  private openDb(): Promise<IDBDatabase> {
    if (this.dbPromise) return this.dbPromise;
    this.dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: 'id' });
          store.createIndex('status', 'status', { unique: false });
          store.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return this.dbPromise;
  }

  private put(db: IDBDatabase, item: OfflineIncidente): Promise<void> {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(item);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  private getAll(db: IDBDatabase): Promise<OfflineIncidente[]> {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const request = tx.objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result as OfflineIncidente[]);
      request.onerror = () => reject(request.error);
    });
  }

  private delete(db: IDBDatabase, id: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }
}
