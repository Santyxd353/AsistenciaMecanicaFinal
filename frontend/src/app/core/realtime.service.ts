/**
 * Realtime WebSocket service.
 *
 * Maneja conexiones WS al backend con:
 *   * Autenticación por query-param `?token=` (el WS spec no permite headers
 *     custom en el handshake del browser, así que el token se pasa en URL).
 *   * Reconexión automática con exponential backoff (1s → 2s → 4s → 8s → 16s,
 *     tope 30s) hasta `MAX_RETRIES` intentos consecutivos. El contador se
 *     resetea cuando llega un mensaje real (no solo el server.ping).
 *   * Heartbeat aplicación: envía `"ping"` cada 20s y espera `pong`. Si no
 *     llega `pong` en 10s asumimos zombie connection y forzamos reconexión.
 *   * Multi-sala: el servicio mantiene un Map<roomKey, RoomState>. Suscribirse
 *     a la misma sala desde varios componentes comparte el mismo socket.
 *
 * Cada sala expone un `Observable<RealtimeEvent>` que emite cada evento
 * recibido del servidor (`event`/`payload` JSON).
 */

import { Injectable, OnDestroy, inject } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { filter, share } from 'rxjs/operators';
import { AuthService } from './auth.service';

export interface RealtimeEvent {
  event: string;
  payload: unknown;
}

export type RoomKind = 'solicitud' | 'taller' | 'tecnico' | 'chat';

interface RoomState {
  socket: WebSocket | null;
  subject: Subject<RealtimeEvent>;
  retries: number;
  heartbeat?: ReturnType<typeof setInterval>;
  pongTimeout?: ReturnType<typeof setTimeout>;
  closed: boolean;
  refCount: number;
}

const HEARTBEAT_INTERVAL_MS = 20_000;
const PONG_TIMEOUT_MS = 10_000;
const MAX_RETRIES = 8;

function backoffMs(attempt: number): number {
  // 1s, 2s, 4s, 8s, 16s, 30s, 30s, 30s ...
  return Math.min(30_000, 1000 * Math.pow(2, attempt));
}

@Injectable({ providedIn: 'root' })
export class RealtimeService implements OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly rooms = new Map<string, RoomState>();
  private readonly statusSubject = new BehaviorSubject<'idle' | 'connecting' | 'open' | 'closed' | 'error'>('idle');
  readonly status$ = this.statusSubject.asObservable();

  private get wsBaseUrl(): string {
    // Resolución: si está corriendo en HTTPS usamos wss://, sino ws://.
    // Asumimos que el backend está en :8000 del mismo host. En producción
    // se debería leer desde environment.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.hostname}:8000/api/v1/ws`;
  }

  private buildUrl(kind: RoomKind, id: number, token: string): string {
    const map: Record<RoomKind, string> = {
      solicitud: 'solicitudes',
      taller: 'talleres',
      tecnico: 'tecnicos',
      chat: 'chat',
    };
    return `${this.wsBaseUrl}/${map[kind]}/${id}?token=${encodeURIComponent(token)}`;
  }

  /**
   * Suscribirse a una sala. Devuelve un Observable que emite cada evento.
   * Cuando se cancele la última suscripción a esa sala el socket se cierra.
   */
  subscribe(kind: RoomKind, id: number): Observable<RealtimeEvent> {
    const key = `${kind}:${id}`;
    let state = this.rooms.get(key);

    if (!state) {
      state = {
        socket: null,
        subject: new Subject<RealtimeEvent>(),
        retries: 0,
        closed: false,
        refCount: 0,
      };
      this.rooms.set(key, state);
      this.openSocket(kind, id, state);
    }

    state.refCount += 1;
    return new Observable<RealtimeEvent>((observer) => {
      const sub = state!.subject.subscribe(observer);
      return () => {
        sub.unsubscribe();
        state!.refCount -= 1;
        if (state!.refCount <= 0) {
          this.closeRoom(key);
        }
      };
    }).pipe(share());
  }

  /** Filtro de conveniencia: solo eventos de un nombre concreto. */
  events(kind: RoomKind, id: number, eventName: string): Observable<unknown> {
    return this.subscribe(kind, id).pipe(
      filter((message) => message.event === eventName),
    );
  }

  /** Envía texto al socket de la sala (usado para `ping`/comandos). */
  send(kind: RoomKind, id: number, payload: string): void {
    const state = this.rooms.get(`${kind}:${id}`);
    if (state?.socket && state.socket.readyState === WebSocket.OPEN) {
      state.socket.send(payload);
    }
  }

  ngOnDestroy(): void {
    for (const key of [...this.rooms.keys()]) {
      this.closeRoom(key);
    }
  }

  // --------------------------------------------------------------------
  // internal

  private openSocket(kind: RoomKind, id: number, state: RoomState): void {
    // El servicio Auth persiste el JWT en `localStorage` bajo la clave `token`
    // (ver `auth.service.ts#persistSession`). Si en el futuro se agrega un
    // método `getAccessToken()` lo preferimos para encapsular esa decisión.
    const token = ((this.auth as unknown) as { getAccessToken?: () => string }).getAccessToken?.()
      ?? localStorage.getItem('token');
    if (!token) {
      // Sin token no podemos abrir el WS. Reintentamos cuando el usuario haga login.
      this.statusSubject.next('error');
      return;
    }

    const url = this.buildUrl(kind, id, token);
    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch (err) {
      console.error('[realtime] no se pudo crear el WebSocket', err);
      this.scheduleReconnect(kind, id, state);
      return;
    }

    state.socket = socket;
    state.closed = false;
    this.statusSubject.next('connecting');

    socket.onopen = () => {
      state.retries = 0;
      this.statusSubject.next('open');
      this.startHeartbeat(state);
    };

    socket.onmessage = (msg) => {
      let parsed: RealtimeEvent | null = null;
      try {
        parsed = JSON.parse(msg.data);
      } catch {
        return;
      }
      if (!parsed) return;
      if (parsed.event === 'pong' || parsed.event === 'server.ping') {
        // Heartbeat: cancelamos el timeout de pong y respondemos a server.ping
        // implícitamente con TCP keep-alive.
        this.cancelPongTimeout(state);
        return;
      }
      state.subject.next(parsed);
    };

    socket.onerror = (event) => {
      console.warn('[realtime] socket error', event);
      this.statusSubject.next('error');
    };

    socket.onclose = () => {
      this.stopHeartbeat(state);
      if (state.closed) {
        this.statusSubject.next('closed');
        return;
      }
      this.scheduleReconnect(kind, id, state);
    };
  }

  private startHeartbeat(state: RoomState): void {
    this.stopHeartbeat(state);
    state.heartbeat = setInterval(() => {
      if (state.socket?.readyState !== WebSocket.OPEN) return;
      state.socket.send('ping');
      state.pongTimeout = setTimeout(() => {
        // Sin pong → conexión zombie, forzamos cierre para que dispare reconnect.
        try {
          state.socket?.close(4000, 'pong-timeout');
        } catch {
          /* ignore */
        }
      }, PONG_TIMEOUT_MS);
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(state: RoomState): void {
    if (state.heartbeat) {
      clearInterval(state.heartbeat);
      state.heartbeat = undefined;
    }
    this.cancelPongTimeout(state);
  }

  private cancelPongTimeout(state: RoomState): void {
    if (state.pongTimeout) {
      clearTimeout(state.pongTimeout);
      state.pongTimeout = undefined;
    }
  }

  private scheduleReconnect(kind: RoomKind, id: number, state: RoomState): void {
    if (state.closed) return;
    if (state.retries >= MAX_RETRIES) {
      console.warn('[realtime] máximo de reconexiones alcanzado para', kind, id);
      this.statusSubject.next('closed');
      return;
    }
    const delay = backoffMs(state.retries);
    state.retries += 1;
    setTimeout(() => {
      if (state.closed) return;
      this.openSocket(kind, id, state);
    }, delay);
  }

  private closeRoom(key: string): void {
    const state = this.rooms.get(key);
    if (!state) return;
    state.closed = true;
    this.stopHeartbeat(state);
    try {
      state.socket?.close(1000, 'client-closed');
    } catch {
      /* ignore */
    }
    state.subject.complete();
    this.rooms.delete(key);
  }
}
