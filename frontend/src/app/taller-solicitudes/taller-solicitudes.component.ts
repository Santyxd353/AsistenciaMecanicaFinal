import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Subscription, forkJoin } from 'rxjs';

import { Solicitud, SolicitudService } from '../core/incident.service';
import {
  MapaGeolocalizacionComponent,
  PuntoMapaGeolocalizacion
} from '../mapa/geolocalizacion/mapa-geolocalizacion.component';
import { Tecnico, TecnicoService } from '../core/tecnico.service';
import { Taller, WorkshopProfileService } from '../core/workshop-profile.service';
import { RealtimeEvent, RealtimeService } from '../core/realtime.service';
import { CotizacionService } from '../core/cotizacion.service';

@Component({
  selector: 'app-taller-solicitudes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MapaGeolocalizacionComponent],
  templateUrl: './taller-solicitudes.component.html',
  styleUrl: './taller-solicitudes.component.css'
})
export class TallerSolicitudesComponent implements OnInit, OnDestroy {
  pendientes: Solicitud[] = [];
  misSolicitudes: Solicitud[] = [];
  tecnicos: Tecnico[] = [];
  tallerActual: Taller | null = null;
  cargando = true;
  error = '';
  aceptandoSolicitud = false;
  errorAceptarSolicitud = '';
  asignandoTecnico = false;
  errorAsignarTecnico = '';
  cancelandoSolicitud = false;
  errorCancelarSolicitud = '';
  guardandoCostoSolicitud = false;
  errorCostoSolicitud = '';
  mensajeCostoSolicitud = '';
  guardandoCotizacion = false;
  errorCotizacion = '';
  mensajeCotizacion = '';
  montoCobro: number | null = null;
  cotizacionDraft = {
    costo_estimado: null as number | null,
    tiempo_reparacion_horas: 1,
    eta_llegada_minutos: 20,
    descripcion: '',
    incluye_repuestos: false,
    garantia_dias: 30
  };
  tecnicoSeleccionadoId: number | null = null;
  vistaActiva: 'pendientes' | 'mis-solicitudes' = 'pendientes';
  solicitudSeleccionada: Solicitud | null = null;
  mostrandoNuevaSolicitud = false;
  creandoSolicitud = false;
  errorNuevaSolicitud = '';
  nuevaSolicitud = {
    descripcion: '',
    latitud: null as number | null,
    longitud: null as number | null,
    vehiculo_id: null as number | null
  };
  private readonly backendBaseUrl = 'http://localhost:8000';
  private detalleRealtimeSub?: Subscription;
  private tallerRealtimeSub?: Subscription;

  constructor(
    private solicitudService: SolicitudService,
    private tecnicoService: TecnicoService,
    private workshopProfileService: WorkshopProfileService,
    private realtimeService: RealtimeService,
    private cotizacionService: CotizacionService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
    this.cargarTecnicos();
    this.cargarTallerActual();
  }

  ngOnDestroy(): void {
    this.detalleRealtimeSub?.unsubscribe();
    this.tallerRealtimeSub?.unsubscribe();
  }

  etiquetaEstado(estado: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente',
      buscando_taller: 'Buscando taller',
      asignada: 'Asignada',
      tecnico_en_camino: 'Técnico en camino',
      tecnico_llego: 'Técnico llegó',
      en_proceso: 'En proceso',
      finalizado: 'Finalizado',
      cancelado: 'Cancelado',
      en_progreso: 'En progreso',
      resuelta: 'Finalizado',
      cancelada: 'Cancelado',
      pendiente_sync: 'Pendiente sync'
    };

    return map[estado] ?? estado;
  }

  resumenSeguimiento(solicitud: Solicitud): string {
    if (!solicitud.taller_id) {
      return 'Disponible para que tu taller la tome.';
    }

    if (!solicitud.tecnico_id) {
      return 'Tu taller ya la aceptó. Falta asignar un mecánico.';
    }

    const map: Record<string, string> = {
      pendiente: 'Aceptada por el taller y esperando asignacion operativa.',
      buscando_taller: 'Buscando el taller con mejor disponibilidad.',
      asignada: 'Mecánico asignado. Lista para iniciar atención.',
      tecnico_en_camino: 'El mecánico está en camino.',
      tecnico_llego: 'El mecánico llegó al incidente.',
      en_proceso: 'El mecánico ya se encuentra trabajando en el servicio.',
      finalizado: 'Servicio finalizado correctamente.',
      cancelado: 'El servicio fue cancelado.',
      en_progreso: 'El mecánico ya se encuentra trabajando en el servicio.',
      resuelta: 'Servicio finalizado correctamente.',
      cancelada: 'El servicio fue cancelado.'
    };

    return map[solicitud.estado] ?? 'Estado en seguimiento.';
  }

  etapaSeguimiento(solicitud: Solicitud): string {
    if (!solicitud.taller_id) {
      return 'Por tomar';
    }

    if (!solicitud.tecnico_id) {
      return 'Pendiente de mecánico';
    }

    const map: Record<string, string> = {
      pendiente: 'Pendiente de mecánico',
      buscando_taller: 'Buscando taller',
      asignada: 'Mecánico asignado',
      tecnico_en_camino: 'En camino',
      tecnico_llego: 'En sitio',
      en_proceso: 'En servicio',
      finalizado: 'Servicio resuelto',
      cancelado: 'Servicio cancelado',
      en_progreso: 'En servicio',
      resuelta: 'Servicio resuelto',
      cancelada: 'Servicio cancelado'
    };

    return map[solicitud.estado] ?? this.etiquetaEstado(solicitud.estado);
  }

  progresoSeguimiento(solicitud: Solicitud): number {
    if (!solicitud.taller_id) {
      return 0;
    }

    if (!solicitud.tecnico_id) {
      return 35;
    }

    const map: Record<string, number> = {
      pendiente: 35,
      buscando_taller: 15,
      asignada: 65,
      tecnico_en_camino: 75,
      tecnico_llego: 82,
      en_proceso: 90,
      finalizado: 100,
      cancelado: 100,
      en_progreso: 85,
      resuelta: 100,
      cancelada: 100
    };

    return map[solicitud.estado] ?? 35;
  }

  tieneCoordenadasValidas(solicitud: Solicitud): boolean {
    return Number.isFinite(solicitud.latitud)
      && Number.isFinite(solicitud.longitud)
      && solicitud.latitud >= -90
      && solicitud.latitud <= 90
      && solicitud.longitud >= -180
      && solicitud.longitud <= 180;
  }

  obtenerUrlGoogleMaps(solicitud: Solicitud): string {
    return `https://www.google.com/maps?q=${solicitud.latitud},${solicitud.longitud}`;
  }

  obtenerPuntosMapa(solicitud: Solicitud): PuntoMapaGeolocalizacion[] {
    const puntos: PuntoMapaGeolocalizacion[] = [
      {
        latitud: solicitud.latitud,
        longitud: solicitud.longitud,
        etiqueta: `Incidente de la solicitud #${solicitud.id}`,
        tipo: 'incidente'
      }
    ];

    if (this.tallerActual) {
      puntos.push({
        latitud: this.tallerActual.latitud ?? null,
        longitud: this.tallerActual.longitud ?? null,
        etiqueta: this.tallerActual.nombre_comercial || 'Taller actual',
        tipo: 'taller'
      });
    }

    if (solicitud.tecnico_id) {
      const tecnico = this.tecnicos.find((item) => item.id === solicitud.tecnico_id);

      if (tecnico) {
        puntos.push({
          latitud: solicitud.tecnico_latitud ?? tecnico.latitud ?? null,
          longitud: solicitud.tecnico_longitud ?? tecnico.longitud ?? null,
          etiqueta: tecnico.nombre || 'Mecánico asignado',
          tipo: 'tecnico'
        });
      }
    }

    return puntos;
  }

  obtenerAudioUrl(solicitud: Solicitud): string | null {
    if (!solicitud.audio_url) {
      return null;
    }
    return solicitud.audio_url.startsWith('http')
      ? solicitud.audio_url
      : `${this.backendBaseUrl}${solicitud.audio_url}`;
  }

  obtenerUrlRuta(solicitud: Solicitud): string {
    const originLat = solicitud.tecnico_latitud ?? this.tallerActual?.latitud;
    const originLng = solicitud.tecnico_longitud ?? this.tallerActual?.longitud;
    const destination = `${solicitud.latitud},${solicitud.longitud}`;
    if (originLat != null && originLng != null) {
      return `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLng}&destination=${destination}&travelmode=driving`;
    }
    return `https://www.google.com/maps/dir/?api=1&destination=${destination}&travelmode=driving`;
  }

  cambiarVista(vista: 'pendientes' | 'mis-solicitudes'): void {
    this.vistaActiva = vista;
  }

  abrirDetalle(solicitud: Solicitud): void {
    this.errorAceptarSolicitud = '';
    this.aceptandoSolicitud = false;
    this.errorAsignarTecnico = '';
    this.asignandoTecnico = false;
    this.errorCancelarSolicitud = '';
    this.cancelandoSolicitud = false;
    this.errorCostoSolicitud = '';
    this.mensajeCostoSolicitud = '';
    this.guardandoCostoSolicitud = false;
    this.errorCotizacion = '';
    this.mensajeCotizacion = '';
    this.guardandoCotizacion = false;
    this.montoCobro = solicitud.precio_cobrado ?? null;
    this.cotizacionDraft = {
      costo_estimado: solicitud.precio_cobrado ?? null,
      tiempo_reparacion_horas: 1,
      eta_llegada_minutos: solicitud.tiempo_estimado_minutos ?? 20,
      descripcion: '',
      incluye_repuestos: false,
      garantia_dias: 30
    };
    this.tecnicoSeleccionadoId = solicitud.tecnico_id ?? null;
    this.solicitudSeleccionada = solicitud;
    this.conectarSolicitudRealtime(solicitud);
  }

  cerrarDetalle(): void {
    this.errorAceptarSolicitud = '';
    this.aceptandoSolicitud = false;
    this.errorAsignarTecnico = '';
    this.asignandoTecnico = false;
    this.errorCancelarSolicitud = '';
    this.cancelandoSolicitud = false;
    this.errorCostoSolicitud = '';
    this.mensajeCostoSolicitud = '';
    this.guardandoCostoSolicitud = false;
    this.errorCotizacion = '';
    this.mensajeCotizacion = '';
    this.guardandoCotizacion = false;
    this.montoCobro = null;
    this.tecnicoSeleccionadoId = null;
    this.solicitudSeleccionada = null;
    this.detalleRealtimeSub?.unsubscribe();
    this.detalleRealtimeSub = undefined;
  }

  get comisionCobroLabel(): string {
    if (this.montoCobro === null || !Number.isFinite(Number(this.montoCobro)) || Number(this.montoCobro) <= 0) {
      return 'Pendiente';
    }
    return `Bs ${(Number(this.montoCobro) * 0.10).toFixed(2)}`;
  }

  guardarCostoSolicitud(): void {
    if (!this.solicitudSeleccionada) {
      return;
    }

    const monto = Number(this.montoCobro);
    if (!Number.isFinite(monto) || monto <= 0) {
      this.errorCostoSolicitud = 'Ingresa un monto valido para cobrar.';
      this.mensajeCostoSolicitud = '';
      return;
    }

    this.guardandoCostoSolicitud = true;
    this.errorCostoSolicitud = '';
    this.mensajeCostoSolicitud = '';

    this.solicitudService.actualizarCosto(this.solicitudSeleccionada.id, monto).subscribe({
      next: (solicitudActualizada) => {
        this.solicitudSeleccionada = solicitudActualizada;
        this.montoCobro = solicitudActualizada.precio_cobrado ?? monto;
        this.guardandoCostoSolicitud = false;
        this.mensajeCostoSolicitud = 'Monto actualizado para la pasarela QR.';
        this.cargarSolicitudes();
      },
      error: (error) => {
        this.errorCostoSolicitud = error?.error?.detail || 'No se pudo actualizar el monto.';
        this.guardandoCostoSolicitud = false;
      }
    });
  }

  get puedeCotizarSolicitud(): boolean {
    return !!this.solicitudSeleccionada
      && ['pendiente', 'buscando_taller'].includes(this.solicitudSeleccionada.estado);
  }

  enviarCotizacion(): void {
    if (!this.solicitudSeleccionada) {
      return;
    }

    const costo = Number(this.cotizacionDraft.costo_estimado);
    const eta = Number(this.cotizacionDraft.eta_llegada_minutos);
    const horas = Number(this.cotizacionDraft.tiempo_reparacion_horas);
    if (!Number.isFinite(costo) || costo <= 0 || !Number.isFinite(eta) || eta <= 0 || !Number.isFinite(horas) || horas <= 0) {
      this.errorCotizacion = 'Costo, ETA y horas deben ser valores positivos.';
      this.mensajeCotizacion = '';
      return;
    }

    this.guardandoCotizacion = true;
    this.errorCotizacion = '';
    this.mensajeCotizacion = '';
    this.cotizacionService.crear(this.solicitudSeleccionada.id, {
      costo_estimado: costo,
      eta_llegada_minutos: eta,
      tiempo_reparacion_horas: horas,
      descripcion: this.cotizacionDraft.descripcion.trim(),
      incluye_repuestos: this.cotizacionDraft.incluye_repuestos,
      garantia_dias: Number(this.cotizacionDraft.garantia_dias) || 0,
    }).subscribe({
      next: () => {
        this.guardandoCotizacion = false;
        this.mensajeCotizacion = 'Cotizacion enviada al cliente.';
      },
      error: (error) => {
        this.guardandoCotizacion = false;
        this.errorCotizacion = error?.error?.detail || 'No se pudo enviar la cotización.';
      }
    });
  }

  aceptarSolicitudSeleccionada(): void {
    if (!this.solicitudSeleccionada || !['pendiente', 'buscando_taller'].includes(this.solicitudSeleccionada.estado)) {
      return;
    }

    this.aceptandoSolicitud = true;
    this.errorAceptarSolicitud = '';

    this.solicitudService.aceptarSolicitud(this.solicitudSeleccionada.id).subscribe({
      next: (solicitudActualizada) => {
        this.solicitudSeleccionada = solicitudActualizada;
        this.tecnicoSeleccionadoId = null;
        this.vistaActiva = 'mis-solicitudes';
        this.aceptandoSolicitud = false;
        this.cargarSolicitudes();
      },
      error: (error) => {
        this.errorAceptarSolicitud = error?.error?.detail || 'No se pudo aceptar la solicitud.';
        this.aceptandoSolicitud = false;
      }
    });
  }

  get tecnicosAsignables(): Tecnico[] {
    return this.tecnicos.filter((tecnico) => tecnico.activo && tecnico.disponible);
  }

  get puedeAceptarSolicitud(): boolean {
    return !!this.solicitudSeleccionada
      && ['pendiente', 'buscando_taller'].includes(this.solicitudSeleccionada.estado)
      && !this.solicitudSeleccionada.taller_id;
  }

  get puedeAsignarTecnico(): boolean {
    return !!this.solicitudSeleccionada
      && !!this.solicitudSeleccionada.taller_id
      && !this.solicitudSeleccionada.tecnico_id;
  }

  get puedeCancelarSolicitud(): boolean {
    return !!this.solicitudSeleccionada
      && !!this.solicitudSeleccionada.taller_id
      && !['resuelta', 'finalizado', 'cancelada', 'cancelado'].includes(this.solicitudSeleccionada.estado);
  }

  asignarTecnicoSeleccionado(): void {
    if (!this.solicitudSeleccionada || !this.tecnicoSeleccionadoId) {
      this.errorAsignarTecnico = 'Debes seleccionar un mecanico disponible.';
      return;
    }

    this.asignandoTecnico = true;
    this.errorAsignarTecnico = '';

    this.solicitudService.asignarTecnico(this.solicitudSeleccionada.id, this.tecnicoSeleccionadoId).subscribe({
      next: (solicitudActualizada) => {
        this.solicitudSeleccionada = solicitudActualizada;
        this.tecnicoSeleccionadoId = solicitudActualizada.tecnico_id ?? null;
        this.asignandoTecnico = false;
        this.cargarSolicitudes();
        this.cargarTecnicos();
      },
      error: (error) => {
        this.errorAsignarTecnico = error?.error?.detail || 'No se pudo asignar el mecánico.';
        this.asignandoTecnico = false;
      }
    });
  }

  cancelarSolicitudSeleccionada(): void {
    if (!this.solicitudSeleccionada) {
      return;
    }

    this.cancelandoSolicitud = true;
    this.errorCancelarSolicitud = '';

    this.solicitudService.cancelarSolicitud(this.solicitudSeleccionada.id).subscribe({
      next: (solicitudActualizada) => {
        this.solicitudSeleccionada = solicitudActualizada;
        this.tecnicoSeleccionadoId = solicitudActualizada.tecnico_id ?? null;
        this.cancelandoSolicitud = false;
        this.cargarSolicitudes();
        this.cargarTecnicos();
      },
      error: (error) => {
        this.errorCancelarSolicitud = error?.error?.detail || 'No se pudo cancelar la solicitud.';
        this.cancelandoSolicitud = false;
      }
    });
  }

  abrirNuevaSolicitud(): void {
    this.errorNuevaSolicitud = '';
    this.mostrandoNuevaSolicitud = true;
  }

  cerrarNuevaSolicitud(): void {
    this.mostrandoNuevaSolicitud = false;
    this.creandoSolicitud = false;
    this.errorNuevaSolicitud = '';
    this.nuevaSolicitud = {
      descripcion: '',
      latitud: null,
      longitud: null,
      vehiculo_id: null
    };
  }

  crearSolicitudPrueba(): void {
    if (
      !this.nuevaSolicitud.descripcion.trim() ||
      this.nuevaSolicitud.latitud === null ||
      this.nuevaSolicitud.longitud === null
    ) {
      this.errorNuevaSolicitud = 'Descripcion, latitud y longitud son obligatorias.';
      return;
    }

    this.creandoSolicitud = true;
    this.errorNuevaSolicitud = '';

    const payload: Partial<Solicitud> = {
      descripcion: this.nuevaSolicitud.descripcion.trim(),
      latitud: this.nuevaSolicitud.latitud,
      longitud: this.nuevaSolicitud.longitud
    };

    if (this.nuevaSolicitud.vehiculo_id !== null) {
      payload.vehiculo_id = this.nuevaSolicitud.vehiculo_id;
    }

    this.solicitudService.createSolicitud(payload).subscribe({
      next: () => {
        this.vistaActiva = 'pendientes';
        this.cerrarNuevaSolicitud();
        this.cargarSolicitudes();
      },
      error: (error) => {
        this.errorNuevaSolicitud = error?.error?.detail || 'No se pudo crear la solicitud de prueba.';
        this.creandoSolicitud = false;
      }
    });
  }

  onOverlayClick(event: Event): void {
    if ((event.target as HTMLElement).classList.contains('taller-solicitudes-modal-overlay')) {
      this.cerrarDetalle();
      this.cerrarNuevaSolicitud();
    }
  }

  private cargarSolicitudes(): void {
    this.cargando = true;
    this.error = '';

    forkJoin({
      pendientes: this.solicitudService.getSolicitudesPendientesTaller(),
      misSolicitudes: this.solicitudService.getMisSolicitudesTaller()
    }).subscribe({
      next: ({ pendientes, misSolicitudes }) => {
        this.pendientes = Array.isArray(pendientes) ? pendientes : [];
        this.misSolicitudes = Array.isArray(misSolicitudes) ? misSolicitudes : [];
        this.cargando = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.error = error?.error?.detail || 'No se pudieron cargar las solicitudes del taller.';
        this.cargando = false;
        this.cdr.detectChanges();
      }
    });
  }

  private cargarTecnicos(): void {
    this.tecnicoService.getTecnicos().subscribe({
      next: (tecnicos) => {
        this.tecnicos = Array.isArray(tecnicos) ? tecnicos : [];
        this.cdr.detectChanges();
      },
      error: () => {
        this.tecnicos = [];
        this.cdr.detectChanges();
      }
    });
  }

  private cargarTallerActual(): void {
    this.workshopProfileService.getMyWorkshop().subscribe({
      next: (taller) => {
        this.tallerActual = taller;
        this.conectarTallerRealtime(taller);
        this.cdr.detectChanges();
      },
      error: () => {
        this.tallerActual = null;
        this.cdr.detectChanges();
      }
    });
  }

  private conectarTallerRealtime(taller: Taller): void {
    this.tallerRealtimeSub?.unsubscribe();
    if (!taller.id) {
      return;
    }
    this.tallerRealtimeSub = this.realtimeService.subscribe('taller', taller.id).subscribe((event) => {
      this.aplicarEventoRealtime(event);
    });
  }

  private conectarSolicitudRealtime(solicitud: Solicitud): void {
    this.detalleRealtimeSub?.unsubscribe();
    if (!solicitud.id || solicitud.id < 0) {
      return;
    }
    this.detalleRealtimeSub = this.realtimeService.subscribe('solicitud', solicitud.id).subscribe((event) => {
      this.aplicarEventoRealtime(event);
    });
  }

  private aplicarEventoRealtime(event: RealtimeEvent): void {
    if (event.event === 'tracking.update') {
      const payload = event.payload as {
        solicitud_id?: number;
        latitud?: number;
        longitud?: number;
        eta_minutos?: number;
        distancia_restante_km?: number;
      };
      if (!payload.solicitud_id) return;
      this.aplicarPatchSolicitud(payload.solicitud_id, {
        tecnico_latitud: payload.latitud,
        tecnico_longitud: payload.longitud,
        tiempo_estimado_minutos: payload.eta_minutos,
        distancia_tecnico_km: payload.distancia_restante_km,
      });
      return;
    }

    if (event.event === 'solicitud.actualizada') {
      const payload = event.payload as Partial<Solicitud>;
      if (payload.id) {
        this.aplicarPatchSolicitud(payload.id, payload);
      }
    }
  }

  private aplicarPatchSolicitud(solicitudId: number, patch: Partial<Solicitud>): void {
    const merge = (item: Solicitud): Solicitud => item.id === solicitudId ? { ...item, ...patch } : item;
    this.pendientes = this.pendientes.map(merge);
    this.misSolicitudes = this.misSolicitudes.map(merge);
    if (this.solicitudSeleccionada?.id === solicitudId) {
      this.solicitudSeleccionada = { ...this.solicitudSeleccionada, ...patch };
    }
    this.cdr.detectChanges();
  }
}
