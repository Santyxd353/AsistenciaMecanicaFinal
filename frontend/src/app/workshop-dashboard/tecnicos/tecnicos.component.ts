import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule, NgForm  } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { Tecnico, TecnicoPayload, TecnicoService, TecnicoUsuarioPayload } from '../../core/tecnico.service';
import { EspecialidadService, Especialidad } from '../../core/especialidad.service';

@Component({
  selector: 'app-tecnicos',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tecnicos.component.html',
  styleUrl: './tecnicos.component.css'
})

export class TecnicosComponent implements OnInit {
  tecnicos: Tecnico[] = [];
  loading = true;

  mostrarModal = false;
  editando = false;
  mostrarModalUsuario = false;
  convirtiendoUsuario = false;
  tecnicoSeleccionadoParaUsuario: Tecnico | null = null;

  filtroEstado: 'todos' | 'disponibles' | 'ocupados' = 'todos';
  busqueda = '';

  guardando = false;
  mensajeExito = '';
  mensajeError = '';

  modalMensajeError = '';
  modalMensajeExito = '';

  especialidades: Especialidad[] = [];
  mostrarNuevaEspecialidad = false;
  nuevaEspecialidad = '';
  especialidadSeleccionadaId = '';
  especialidadesSeleccionadas: Especialidad[] = [];
  usuarioForm = {
    username: '',
    email: '',
    password: ''
  };

  form: any = {
    id: null,
    nombre: '',
    ci: '',
    direccion: '',
    especialidad_ids: [],
    disponible: true,
    activo: true,
    id_usuario: null,
    latitud: null,
    longitud: null
  };

  constructor(
    private tecnicoService: TecnicoService,
    private especialidadService: EspecialidadService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.cargarEspecialidades();
    this.cargar();
  }

  get totalTecnicos(): number {
    return this.tecnicos.length;
  }

  get tecnicosDisponibles(): number {
    return this.tecnicos.filter(t => t.disponible).length;
  }

  get tecnicosOcupados(): number {
    return this.tecnicos.filter(t => !t.disponible).length;
  }

  get tecnicosFiltrados(): Tecnico[] {
    let lista = [...this.tecnicos];

    if (this.filtroEstado === 'disponibles') {
      lista = lista.filter(t => t.disponible);
    }

    if (this.filtroEstado === 'ocupados') {
      lista = lista.filter(t => !t.disponible);
    }

    if (this.busqueda.trim()) {
      const texto = this.busqueda.toLowerCase().trim();
      lista = lista.filter(t =>
        (t.nombre || '').toLowerCase().includes(texto) ||
        (t.ci || '').toLowerCase().includes(texto) ||
        (t.direccion || '').toLowerCase().includes(texto) ||
        this.getEspecialidadesTexto(t).toLowerCase().includes(texto)
      );
    }

    return lista;
  }

  cargar() {
    this.loading = true;

    this.tecnicoService.getTecnicos().subscribe({
      next: (res: any) => {
        this.tecnicos = Array.isArray(res) ? res : [];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err: unknown) => {
        console.error(err);
        this.loading = false;
        this.mensajeError = 'No se pudieron cargar los técnicos.';
        this.cdr.detectChanges();
      }
    });
  }

  cargarEspecialidades() {
    this.especialidadService.getEspecialidades().subscribe({
      next: (res: Especialidad[]) => {
        this.especialidades = res;
        this.cdr.detectChanges();
      },
      error: (err: unknown) => {
        console.error(err);
      }
    });
  }

  onEspecialidadChange(valor: string) {
    this.modalMensajeError = '';
    this.mostrarNuevaEspecialidad = valor === '__nueva__';

    if (this.mostrarNuevaEspecialidad) {
      this.nuevaEspecialidad = '';
    } else {
      this.nuevaEspecialidad = '';
    }
  }

  crearEspecialidadYAgregar(): void {
    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    const nombreNueva = this.nuevaEspecialidad.trim();
    if (!nombreNueva) {
      this.modalMensajeError = 'Debes ingresar el nombre de la nueva especialidad.';
      return;
    }

    if (nombreNueva.length < 3) {
      this.modalMensajeError = 'La especialidad debe tener al menos 3 caracteres.';
      return;
    }

    const existe = this.especialidades.find(
      esp => esp.nombre.trim().toLowerCase() === nombreNueva.toLowerCase()
    );

    if (existe) {
      const yaSeleccionada = this.especialidadesSeleccionadas.some(item => item.id === existe.id);
      if (!yaSeleccionada) {
        this.especialidadesSeleccionadas = [...this.especialidadesSeleccionadas, existe];
        this.syncEspecialidadesSeleccionadas();
      }
      this.modalMensajeExito = 'La especialidad ya existía y fue agregada a la selección.';
      this.nuevaEspecialidad = '';
      this.especialidadSeleccionadaId = '';
      this.mostrarNuevaEspecialidad = false;
      return;
    }

    this.especialidadService.crearEspecialidad(nombreNueva).subscribe({
      next: (especialidadCreada) => {
        this.especialidades = [...this.especialidades, especialidadCreada]
          .sort((a, b) => a.nombre.localeCompare(b.nombre));
        this.especialidadesSeleccionadas = [...this.especialidadesSeleccionadas, especialidadCreada];
        this.syncEspecialidadesSeleccionadas();
        this.nuevaEspecialidad = '';
        this.especialidadSeleccionadaId = '';
        this.mostrarNuevaEspecialidad = false;
        this.modalMensajeExito = 'Especialidad creada y agregada correctamente.';
        this.cdr.detectChanges();
      },
      error: (err: unknown) => {
        console.error(err);
        this.modalMensajeError = 'No se pudo crear la nueva especialidad.';
      }
    });
  }

  manejarEnterNuevaEspecialidad(event: Event): void {
    event.preventDefault();
    this.crearEspecialidadYAgregar();
  }

  volverAlPanel() {
    this.router.navigate(['/taller']);
  }

  nuevo() {
    this.mensajeExito = '';
    this.mensajeError = '';
    this.guardando = false;

    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    this.mostrarNuevaEspecialidad = false;
    this.nuevaEspecialidad = '';

    this.form = {
      id: null,
      nombre: '',
      ci: '',
      direccion: '',
      especialidad_ids: [],
      disponible: true,
      activo: true,
      id_usuario: null,
      latitud: null,
      longitud: null
    };
    this.especialidadSeleccionadaId = '';
    this.especialidadesSeleccionadas = [];

    this.editando = false;
    this.mostrarModal = true;
  }

  editar(t: Tecnico) {
    this.mensajeExito = '';
    this.mensajeError = '';
    this.guardando = false;

    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    this.mostrarNuevaEspecialidad = false;
    this.nuevaEspecialidad = '';

    this.form = {
      ...t,
      ci: t.ci ?? '',
      direccion: t.direccion ?? '',
      especialidad_ids: (t.especialidades || []).map(esp => esp.id),
      disponible: t.disponible ?? true,
      activo: t.activo ?? true,
      id_usuario: t.id_usuario ?? null,
      latitud: t.latitud ?? null,
      longitud: t.longitud ?? null
    };
    this.especialidadesSeleccionadas = [...(t.especialidades || [])];
    this.especialidadSeleccionadaId = '';

    this.editando = true;
    this.mostrarModal = true;
  }

  cerrarModal() {
    this.mostrarModal = false;
    this.editando = false;
    this.guardando = false;

    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    this.form = {
      id: null,
      nombre: '',
      ci: '',
      direccion: '',
      especialidad_ids: [],
      disponible: true,
      activo: true,
      id_usuario: null,
      latitud: null,
      longitud: null
    };
    this.especialidadSeleccionadaId = '';
    this.especialidadesSeleccionadas = [];

    this.cdr.detectChanges();
  }

  guardar(formulario: NgForm) {
    this.mensajeExito = '';
    this.mensajeError = '';
    this.guardando = true;

    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    const nombreLimpio = (this.form.nombre || '').trim();

    if (formulario.invalid) {
      formulario.control.markAllAsTouched();
      this.modalMensajeError = 'Completa correctamente los campos obligatorios.';
      this.guardando = false;
      return;
    }

    if (this.mostrarNuevaEspecialidad) {
      this.modalMensajeError = 'Primero crea y agrega la nueva especialidad antes de guardar el técnico.';
      this.guardando = false;
      return;
    }

    if (!this.especialidadesSeleccionadas.length) {
      this.modalMensajeError = 'Debes agregar al menos una especialidad.';
      this.guardando = false;
      return;
    }

    this.guardarTecnico(this.buildPayload(nombreLimpio));
  }

  guardarTecnico(payload: TecnicoPayload) {
    if (this.editando) {
      this.tecnicoService.actualizarTecnico(this.form.id, payload).subscribe({
        next: (res: Tecnico) => {
          const credenciales = res.usuario_username && res.password_temporal
            ? ` Usuario: ${res.usuario_username} | Contraseña temporal: ${res.password_temporal}`
            : '';
          this.mensajeExito = `Mecánico creado correctamente.${credenciales}`;
          this.cerrarModal();
          setTimeout(() => this.cargar(), 0);
        },
        error: (err: unknown) => {
          console.error(err);
          this.mensajeError = this.obtenerMensajeError(err, 'No se pudo actualizar el técnico.');
          this.guardando = false;
        },
        complete: () => {
          this.guardando = false;
        }
      });
    } else {
      this.tecnicoService.crearTecnico(payload).subscribe({
        next: (res: Tecnico) => {
          const credenciales = res.usuario_username && res.password_temporal
            ? ` Usuario: ${res.usuario_username} | Contraseña temporal: ${res.password_temporal}`
            : '';
          this.mensajeExito = `Mecánico creado correctamente.${credenciales}`;
          this.cerrarModal();
          setTimeout(() => this.cargar(), 0);
        },
        error: (err: unknown) => {
          console.error(err);
          this.mensajeError = this.obtenerMensajeError(err, 'No se pudo crear el técnico.');
          this.guardando = false;
        },
        complete: () => {
          this.guardando = false;
        }
      });
    }
  }

  eliminar(t: Tecnico) {
    this.mensajeExito = '';
    this.mensajeError = '';

    if (confirm(`¿Eliminar al técnico ${t.nombre}?`)) {
      this.tecnicoService.eliminarTecnico(t.id).subscribe({
        next: () => {
          this.mensajeExito = 'Técnico eliminado correctamente.';
          this.cargar();
        },
        error: (err: unknown) => {
          this.mensajeError = 'No se pudo eliminar el técnico.';
        }
      });
    }
  }

  toggleDisponibilidad(t: any) {
    this.mensajeExito = '';
    this.mensajeError = '';

    this.tecnicoService.cambiarDisponibilidad(t.id, !t.disponible).subscribe({
      next: () => {
        this.mensajeExito = `Disponibilidad actualizada para ${t.nombre}.`;
        this.cargar();
      },
      error: (err: unknown) => {
        this.mensajeError = this.obtenerMensajeError(err, 'No se pudo actualizar la disponibilidad.');
      }
    });
  }

  toggleActivo(tecnico: Tecnico): void {
    this.mensajeExito = '';
    this.mensajeError = '';

    const nuevoEstado = !tecnico.activo;
    const payload: TecnicoPayload = {
      nombre: tecnico.nombre,
      ci: tecnico.ci,
      direccion: tecnico.direccion,
      especialidad_ids: (tecnico.especialidades || []).map(item => item.id),
      disponible: tecnico.disponible,
      activo: nuevoEstado,
      latitud: tecnico.latitud ?? null,
      longitud: tecnico.longitud ?? null
    };

    this.tecnicoService.actualizarTecnico(tecnico.id, payload).subscribe({
      next: () => {
        this.mensajeExito = nuevoEstado
          ? `El técnico ${tecnico.nombre} fue reactivado y su acceso al sistema quedó habilitado.`
          : `El técnico ${tecnico.nombre} fue dado de baja y su acceso al sistema quedó deshabilitado.`;
        this.cargar();
      },
      error: (err: unknown) => {
        this.mensajeError = this.obtenerMensajeError(
          err,
          nuevoEstado ? 'No se pudo reactivar el técnico.' : 'No se pudo dar de baja al técnico.'
        );
      }
    });
  }

  abrirModalUsuario(tecnico: Tecnico): void {
    this.mensajeExito = '';
    this.mensajeError = '';
    this.modalMensajeError = '';
    this.modalMensajeExito = '';
    this.tecnicoSeleccionadoParaUsuario = tecnico;
    this.usuarioForm = {
      username: tecnico.nombre ?? '',
      email: '',
      password: tecnico.ci ?? ''
    };
    this.mostrarModalUsuario = true;
  }

  cerrarModalUsuario(): void {
    this.mostrarModalUsuario = false;
    this.convirtiendoUsuario = false;
    this.tecnicoSeleccionadoParaUsuario = null;
    this.modalMensajeError = '';
    this.modalMensajeExito = '';
    this.usuarioForm = {
      username: '',
      email: '',
      password: ''
    };
  }

  convertirAUsuario(formulario: NgForm): void {
    if (!this.tecnicoSeleccionadoParaUsuario) {
      return;
    }

    if (formulario.invalid) {
      formulario.control.markAllAsTouched();
      this.modalMensajeError = 'Completa correctamente las credenciales del nuevo usuario.';
      return;
    }

    this.convirtiendoUsuario = true;
    this.modalMensajeError = '';
    this.modalMensajeExito = '';

    const payload: TecnicoUsuarioPayload = {
      username: this.usuarioForm.username.trim(),
      email: this.usuarioForm.email.trim().toLowerCase(),
      password: this.usuarioForm.password
    };

    this.tecnicoService.convertirATecnicoUsuario(this.tecnicoSeleccionadoParaUsuario.id, payload).subscribe({
      next: () => {
        this.mensajeExito = `El técnico ${this.tecnicoSeleccionadoParaUsuario?.nombre} ahora forma parte del sistema como usuario.`;
        this.cerrarModalUsuario();
        this.cargar();
      },
      error: (err: unknown) => {
        this.modalMensajeError = this.obtenerMensajeError(
          err,
          'No se pudo convertir el técnico en usuario del sistema.'
        );
        this.convirtiendoUsuario = false;
      },
      complete: () => {
        this.convirtiendoUsuario = false;
      }
    });
  }

  agregarEspecialidad(): void {
    this.modalMensajeError = '';

    if (this.especialidadSeleccionadaId === '__nueva__') {
      this.mostrarNuevaEspecialidad = true;
      this.nuevaEspecialidad = '';
      return;
    }

    const id = Number(this.especialidadSeleccionadaId);
    if (!id) {
      return;
    }

    const especialidad = this.especialidades.find(item => item.id === id);
    if (!especialidad) {
      return;
    }

    const yaExiste = this.especialidadesSeleccionadas.some(item => item.id === especialidad.id);
    if (yaExiste) {
      this.especialidadSeleccionadaId = '';
      return;
    }

    this.especialidadesSeleccionadas = [...this.especialidadesSeleccionadas, especialidad];
    this.syncEspecialidadesSeleccionadas();
    this.especialidadSeleccionadaId = '';
  }

  quitarEspecialidad(id: number): void {
    this.especialidadesSeleccionadas = this.especialidadesSeleccionadas.filter(item => item.id !== id);
    this.syncEspecialidadesSeleccionadas();
  }

  getEspecialidadesTexto(tecnico: Tecnico): string {
    return (tecnico.especialidades || []).map(item => item.nombre).join(', ');
  }

  private syncEspecialidadesSeleccionadas(): void {
    this.form.especialidad_ids = this.especialidadesSeleccionadas.map(item => item.id);
  }

  private buildPayload(nombre: string): TecnicoPayload {
    return {
      nombre,
      ci: (this.form.ci || '').trim(),
      direccion: (this.form.direccion || '').trim(),
      especialidad_ids: this.especialidadesSeleccionadas.map(item => item.id),
      disponible: this.form.disponible ?? true,
      activo: this.form.activo ?? true,
      latitud: this.form.latitud ?? null,
      longitud: this.form.longitud ?? null
    };
  }

  private obtenerMensajeError(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;
      if (detail?.code === 'PLAN_LIMIT_TECHNICIAN') {
        this.router.navigate(['/upgrade-plan'], { queryParams: { reason: 'mechanics' } });
        return detail.message || fallback;
      }
      return detail?.message || detail || fallback;
    }
    return fallback;
  }
}

