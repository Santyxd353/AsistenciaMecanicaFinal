import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';

import { Solicitud, SolicitudService } from '../core/incident.service';
import {
  MapaGeolocalizacionComponent,
  PuntoMapaGeolocalizacion
} from '../mapa/geolocalizacion/mapa-geolocalizacion.component';
import { Tecnico, TecnicoService } from '../core/tecnico.service';
import { Taller, WorkshopProfileService } from '../core/workshop-profile.service';

@Component({
  selector: 'app-taller-solicitudes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MapaGeolocalizacionComponent],
  templateUrl: './taller-solicitudes.component.html',
  styleUrl: './taller-solicitudes.component.css'
})
export class TallerSolicitudesComponent implements OnInit {
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

  constructor(
    private solicitudService: SolicitudService,
    private tecnicoService: TecnicoService,
    private workshopProfileService: WorkshopProfileService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
    this.cargarTecnicos();
    this.cargarTallerActual();
  }

  etiquetaEstado(estado: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente',
      asignada: 'Asignada',
      en_progreso: 'En progreso',
      resuelta: 'Resuelta',
      cancelada: 'Cancelada'
    };

    return map[estado] ?? estado;
  }

  resumenSeguimiento(solicitud: Solicitud): string {
    if (!solicitud.taller_id) {
      return 'Disponible para que tu taller la tome.';
    }

    if (!solicitud.tecnico_id) {
      return 'Tu taller ya la acepto. Falta asignar un tecnico.';
    }

    const map: Record<string, string> = {
      pendiente: 'Aceptada por el taller y esperando asignacion operativa.',
      asignada: 'Tecnico asignado. Lista para iniciar atencion.',
      en_progreso: 'El tecnico ya se encuentra trabajando en el servicio.',
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
      return 'Pendiente de tecnico';
    }

    const map: Record<string, string> = {
      pendiente: 'Pendiente de tecnico',
      asignada: 'Tecnico asignado',
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
      asignada: 65,
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
          latitud: tecnico.latitud ?? null,
          longitud: tecnico.longitud ?? null,
          etiqueta: tecnico.nombre || 'Tecnico asignado',
          tipo: 'tecnico'
        });
      }
    }

    return puntos;
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
    this.tecnicoSeleccionadoId = solicitud.tecnico_id ?? null;
    this.solicitudSeleccionada = solicitud;
  }

  cerrarDetalle(): void {
    this.errorAceptarSolicitud = '';
    this.aceptandoSolicitud = false;
    this.errorAsignarTecnico = '';
    this.asignandoTecnico = false;
    this.errorCancelarSolicitud = '';
    this.cancelandoSolicitud = false;
    this.tecnicoSeleccionadoId = null;
    this.solicitudSeleccionada = null;
  }

  aceptarSolicitudSeleccionada(): void {
    if (!this.solicitudSeleccionada || this.solicitudSeleccionada.estado !== 'pendiente') {
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
      && this.solicitudSeleccionada.estado === 'pendiente'
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
      && this.solicitudSeleccionada.estado !== 'resuelta'
      && this.solicitudSeleccionada.estado !== 'cancelada';
  }

  asignarTecnicoSeleccionado(): void {
    if (!this.solicitudSeleccionada || !this.tecnicoSeleccionadoId) {
      this.errorAsignarTecnico = 'Debes seleccionar un tecnico disponible.';
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
        this.errorAsignarTecnico = error?.error?.detail || 'No se pudo asignar el tecnico.';
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
        this.cdr.detectChanges();
      },
      error: () => {
        this.tallerActual = null;
        this.cdr.detectChanges();
      }
    });
  }
}
