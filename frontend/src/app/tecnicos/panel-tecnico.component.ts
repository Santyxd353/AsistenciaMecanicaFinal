import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';

import { AuthService } from '../core/auth.service';
import { Solicitud, SolicitudService } from '../core/incident.service';
import { Tecnico, TecnicoService } from '../core/tecnico.service';

@Component({
  selector: 'app-panel-tecnico',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './panel-tecnico.component.html',
  styleUrl: './panel-tecnico.component.css'
})
export class PanelTecnicoComponent implements OnInit {
  perfilTecnico: Tecnico | null = null;
  cargandoPerfil = true;
  errorPerfil = '';
  asignaciones: Solicitud[] = [];
  cargandoAsignaciones = true;
  errorAsignaciones = '';
  actualizandoDisponibilidad = false;
  actualizandoSolicitudId: number | null = null;

  constructor(
    private authService: AuthService,
    private tecnicoService: TecnicoService,
    private solicitudService: SolicitudService
  ) {}

  ngOnInit(): void {
    this.cargarPerfilTecnico();
    this.cargarAsignaciones();
  }

  get nombreTecnico(): string {
    if (this.perfilTecnico?.nombre?.trim()) {
      return this.perfilTecnico.nombre.trim();
    }
    const currentUser = this.authService.currentUserValue;
    return currentUser?.full_name?.trim() || currentUser?.username || 'Tecnico';
  }

  cerrarSesion(): void {
    this.authService.logout();
  }

  get especialidadesTexto(): string {
    const nombres = (this.perfilTecnico?.especialidades || [])
      .map(item => item.nombre?.trim())
      .filter((nombre): nombre is string => Boolean(nombre));

    return nombres.length > 0 ? nombres.join(', ') : 'Sin especialidades registradas';
  }

  get estadoDisponibilidad(): string {
    if (!this.perfilTecnico) {
      return 'Cargando';
    }
    return this.perfilTecnico.disponible ? 'Disponible' : 'Ocupado';
  }

  get estadoRegistro(): string {
    if (!this.perfilTecnico) {
      return 'Cargando';
    }
    return this.perfilTecnico.activo ? 'Activo' : 'Inactivo';
  }

  get tieneAsignaciones(): boolean {
    return this.asignaciones.length > 0;
  }

  toggleDisponibilidad(): void {
    if (!this.perfilTecnico) {
      return;
    }

    this.actualizandoDisponibilidad = true;
    const nuevoEstado = !this.perfilTecnico.disponible;

    this.tecnicoService.actualizarMiDisponibilidad(nuevoEstado).subscribe({
      next: (perfil) => {
        this.perfilTecnico = perfil;
        this.actualizandoDisponibilidad = false;
      },
      error: () => {
        this.errorPerfil = 'No se pudo actualizar tu disponibilidad.';
        this.actualizandoDisponibilidad = false;
      }
    });
  }

  actualizarEstadoAsignacion(solicitudId: number, estado: string): void {
    this.actualizandoSolicitudId = solicitudId;
    this.errorAsignaciones = '';

    this.solicitudService.actualizarMiAsignacionEstado(solicitudId, estado).subscribe({
      next: (solicitudActualizada) => {
        this.asignaciones = this.asignaciones.map((solicitud) =>
          solicitud.id === solicitudId ? solicitudActualizada : solicitud
        );

        if (estado === 'resuelta' || estado === 'cancelada') {
          this.perfilTecnico = this.perfilTecnico
            ? { ...this.perfilTecnico, disponible: true }
            : this.perfilTecnico;
        }

        if (estado === 'en_progreso' || estado === 'llegada') {
          this.perfilTecnico = this.perfilTecnico
            ? { ...this.perfilTecnico, disponible: false }
            : this.perfilTecnico;
        }

        this.actualizandoSolicitudId = null;
      },
      error: (error) => {
        this.errorAsignaciones = error?.error?.detail || 'No se pudo actualizar el estado de la asignacion.';
        this.actualizandoSolicitudId = null;
      }
    });
  }

  etiquetaEstado(estado: string): string {
    const estados: Record<string, string> = {
      pendiente: 'Pendiente',
      asignada: 'Asignada',
      en_progreso: 'En progreso',
      llegada: 'Mecanico en sitio',
      resuelta: 'Resuelta',
      cancelada: 'Cancelada'
    };

    return estados[estado] || estado;
  }

  private cargarPerfilTecnico(): void {
    this.cargandoPerfil = true;
    this.errorPerfil = '';

    this.tecnicoService.getMiPerfilTecnico().subscribe({
      next: (perfil) => {
        this.perfilTecnico = perfil;
        this.cargandoPerfil = false;
      },
      error: (error) => {
        this.errorPerfil = error?.error?.detail || 'No se pudo cargar el perfil tecnico.';
        this.cargandoPerfil = false;
      }
    });
  }

  private cargarAsignaciones(): void {
    this.cargandoAsignaciones = true;
    this.errorAsignaciones = '';

    this.solicitudService.getMisAsignaciones().subscribe({
      next: (asignaciones) => {
        this.asignaciones = asignaciones;
        this.cargandoAsignaciones = false;
      },
      error: (error) => {
        this.errorAsignaciones = error?.error?.detail || 'No se pudieron cargar tus asignaciones.';
        this.cargandoAsignaciones = false;
      }
    });
  }
}
