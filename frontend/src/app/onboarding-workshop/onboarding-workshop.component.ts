import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import * as L from 'leaflet';

import { AuthService } from '../core/auth.service';
import { OnboardingService } from '../core/onboarding.service';
import { WorkshopSpecialtyService } from '../core/workshop-specialty.service';
import { EspecialidadTaller } from '../core/workshop-profile.service';
import { VehicleTypeService, TipoVehiculo } from '../core/vehicle-type.service';

// Default center: Santa Cruz de la Sierra. Cualquier click reubica el pin.
const DEFAULT_CENTER: [number, number] = [-17.7833, -63.1821];
const DEFAULT_ZOOM = 13;

@Component({
  selector: 'app-onboarding-workshop',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="onboarding">
      <header>
        <p class="kicker">Creacion de taller</p>
        <h1>Configura tu taller</h1>
        <p>Completa los datos administrativos y operativos para activar el panel.</p>
      </header>

      <form class="panel" (ngSubmit)="submit()" #form="ngForm">
        <section>
          <h2>Administrador principal</h2>
          <div class="grid">
            <label>Nombre <input name="firstName" [(ngModel)]="adminFirstName" required></label>
            <label>Apellido <input name="lastName" [(ngModel)]="adminLastName" required></label>
            <label>Email <input name="email" [(ngModel)]="admin.email" required type="email"></label>
            <label>Contraseña <input name="password" [(ngModel)]="admin.password" required minlength="6" type="password"></label>
          </div>
        </section>

        <section>
          <h2>Datos del taller</h2>
          <div class="grid">
            <label>Nombre comercial <input name="nombre" [(ngModel)]="taller.nombre_comercial" required></label>
            <label>Telefono <input name="telefono" [(ngModel)]="taller.telefono" required></label>
            <label>Email contacto <input name="emailContacto" [(ngModel)]="taller.email_contacto" type="email"></label>
            <label class="wide">Direccion <input name="direccion" [(ngModel)]="taller.direccion" required></label>
            <label class="wide">Descripción <textarea name="descripcion" [(ngModel)]="taller.descripcion" rows="3"></textarea></label>
          </div>
        </section>

        <section>
          <h2>Horario de atención</h2>
          <p class="hint">
            Marca los días que abren. El horario base aplica a todos los días marcados;
            si algún día tiene un horario especial, activa "Personalizar" y ajusta sus
            horas (ejemplo: domingo 07:00–14:00).
          </p>

          <div class="base-row">
            <span class="base-label">Horario base</span>
            <input type="time" name="baseStart" [(ngModel)]="horarioBase.start" required>
            <span class="dash">a</span>
            <input type="time" name="baseEnd" [(ngModel)]="horarioBase.end" required>
          </div>

          <div class="days">
            <div class="day-row" *ngFor="let day of DAYS_FULL; let i = index">
              <label class="day-toggle">
                <input type="checkbox" [checked]="diasMarcados[i]" (change)="toggleDay(i)">
                <span>{{ day }}</span>
              </label>
              <ng-container *ngIf="diasMarcados[i]">
                <label class="day-toggle">
                  <input type="checkbox"
                         [checked]="horariosEspeciales[i] != null"
                         (change)="toggleEspecial(i)">
                  <span>Personalizar</span>
                </label>
                <div class="day-time" *ngIf="horariosEspeciales[i]">
                  <input type="time"
                         [ngModel]="horariosEspeciales[i]!.start"
                         (ngModelChange)="setEspecial(i, 'start', $event)"
                         [ngModelOptions]="{standalone: true}">
                  <span class="dash">a</span>
                  <input type="time"
                         [ngModel]="horariosEspeciales[i]!.end"
                         (ngModelChange)="setEspecial(i, 'end', $event)"
                         [ngModelOptions]="{standalone: true}">
                </div>
                <span class="day-summary" *ngIf="!horariosEspeciales[i]">
                  {{ horarioBase.start }} – {{ horarioBase.end }}
                </span>
              </ng-container>
            </div>
          </div>

          <div class="horario-preview" *ngIf="horarioFormatted">
            <strong>Se mostrará como:</strong> {{ horarioFormatted }}
          </div>
          <div class="error" *ngIf="!horarioFormatted">
            Marca al menos un día de atención.
          </div>
        </section>

        <section>
          <h2>Ubicación del taller</h2>
          <p class="hint">
            Mueve el mapa hasta que el pin del centro quede sobre la ubicación de tu taller.
            También puedes usar tu ubicación actual.
          </p>
          <div class="map-row">
            <button type="button" class="ghost" (click)="useMyLocation()" [disabled]="locating">
              {{ locating ? 'Obteniendo...' : '📍 Usar mi ubicación' }}
            </button>
            <span class="coords" *ngIf="taller.latitud != null && taller.longitud != null">
              {{ taller.latitud!.toFixed(6) }}, {{ taller.longitud!.toFixed(6) }}
            </span>
            <span class="coords muted" *ngIf="taller.latitud == null">
              Sin ubicación seleccionada.
            </span>
          </div>
          <div class="map-wrap">
            <div #mapRef class="map"></div>
            <!-- Pin overlay estático: vive sobre el div del mapa, no es un
                 marker de Leaflet. El mapa se mueve por debajo y el pin
                 permanece anclado al centro del viewport. -->
            <div class="center-pin" aria-hidden="true">
              <svg width="36" height="44" viewBox="0 0 32 40" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 1 C7.7 1 1 7.7 1 16 c0 11 15 22 15 22 s15-11 15-22 C31 7.7 24.3 1 16 1 z"
                      fill="#8b5e34" stroke="#2f241d" stroke-width="2"/>
                <circle cx="16" cy="15" r="6" fill="#fff8ef"/>
              </svg>
              <div class="center-pin-shadow"></div>
            </div>
          </div>
        </section>

        <section>
          <h2>Especialidades</h2>
          <p class="hint">Marca todos los servicios mecánicos que ofrece tu taller.</p>
          <div class="specialties">
            <label *ngFor="let item of specialties">
              <input type="checkbox" [checked]="isSelected(item.id)" (change)="toggleSpecialty(item.id)">
              {{ item.nombre }}
            </label>
          </div>
        </section>

        <section>
          <h2>Tipos de vehículos que atienden</h2>
          <p class="hint">
            Marca las categorías de vehículos que pueden recibir servicio en tu taller
            (autos, motos, eléctricos, deportivos, alta gama, etc).
          </p>
          <div class="specialties">
            <label *ngFor="let item of tiposVehiculo">
              <input type="checkbox" [checked]="isTipoSelected(item.id)" (change)="toggleTipoVehiculo(item.id)">
              {{ item.nombre }}
            </label>
          </div>
        </section>

        <div class="error" *ngIf="error">{{ error }}</div>
        <button [disabled]="loading || form.invalid || !selectedSpecialtyIds.length || !selectedTipoVehiculoIds.length || taller.latitud == null || !horarioFormatted">
          {{ loading ? 'Creando...' : 'Crear taller y entrar' }}
        </button>
      </form>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .onboarding{max-width:1100px;margin:0 auto;padding:32px} header{margin-bottom:18px}.kicker{color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:44px} header p{color:#7a6554}.panel{background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:26px;display:grid;gap:26px;box-shadow:0 20px 55px rgba(86,52,28,.10)}
    h2{margin:0 0 14px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.wide{grid-column:1/-1}
    label{display:grid;gap:7px;font-weight:800} input,textarea{border:1px solid #ead7c4;border-radius:12px;padding:13px;font:inherit}
    .specialties{display:flex;gap:10px;flex-wrap:wrap}.specialties label{display:flex;align-items:center;gap:8px;background:#fff8ef;border:1px solid #ead7c4;border-radius:999px;padding:9px 12px}
    button{border:0;border-radius:8px;padding:15px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px}
    button:disabled{opacity:.55;cursor:not-allowed}
    button.ghost{background:transparent;color:#8b5e34;border:1px solid #d9bea0;padding:9px 14px;border-radius:999px;font-weight:800}
    .base-row{display:flex;gap:10px;align-items:center;background:#fff8ef;border:1px solid #ead7c4;border-radius:12px;padding:10px 14px;margin-bottom:14px}
    .base-row .base-label{font-weight:900;color:#4d3a2c;margin-right:6px}
    .base-row input[type=time]{border:1px solid #ead7c4;border-radius:10px;padding:8px;font:inherit}
    .dash{color:#7a6554;font-weight:700}
    .days{display:grid;gap:8px;margin-bottom:14px}
    .day-row{display:flex;gap:14px;align-items:center;flex-wrap:wrap;background:#fff;border:1px solid #ead7c4;border-radius:12px;padding:10px 14px}
    .day-toggle{display:flex;align-items:center;gap:8px;font-weight:800;cursor:pointer;min-width:120px}
    .day-time{display:flex;gap:8px;align-items:center}
    .day-time input{border:1px solid #ead7c4;border-radius:10px;padding:7px;font:inherit}
    .day-summary{color:#7a6554;font-family:Menlo,Consolas,monospace;font-size:13px}
    .horario-preview{background:#f1e8dc;border-radius:10px;padding:10px 14px;color:#4d3a2c;font-size:14px}
    .map-wrap{position:relative;border-radius:14px;overflow:hidden}
    .map{height:340px;border-radius:14px;overflow:hidden;border:1px solid #ead7c4;background:#eee2d2}
    .center-pin{position:absolute;left:50%;top:50%;transform:translate(-50%,calc(-100% + 6px));pointer-events:none;z-index:1000;display:flex;flex-direction:column;align-items:center}
    .center-pin svg{filter:drop-shadow(0 3px 4px rgba(0,0,0,.35))}
    .center-pin-shadow{width:10px;height:4px;border-radius:50%;background:rgba(0,0,0,.35);transform:translateY(-2px)}
    .map-row{display:flex;gap:14px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
    .coords{font-family:Menlo,Consolas,monospace;font-size:12px;color:#4d3a2c}
    .coords.muted{color:#a08a78;font-style:italic}
    .hint{margin:0 0 12px;color:#7a6554;font-size:13px;line-height:1.5}
    @media(max-width:760px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}h1{font-size:34px}}
  `],
})
export class OnboardingWorkshopComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('mapRef', { static: false }) mapRef?: ElementRef<HTMLDivElement>;

  specialties: EspecialidadTaller[] = [];
  selectedSpecialtyIds: number[] = [];
  tiposVehiculo: TipoVehiculo[] = [];
  selectedTipoVehiculoIds: number[] = [];
  loading = false;
  locating = false;
  error = '';

  // El backend acepta `full_name` (un solo string). Mantenemos esa interfaz
  // pero exponemos nombre + apellido en la UI y los concatenamos al enviar.
  adminFirstName = '';
  adminLastName = '';
  admin = { email: '', password: '' };

  taller = {
    nombre_comercial: '',
    direccion: '',
    telefono: '',
    email_contacto: '',
    // Se serializa desde diasMarcados / horarioBase / horariosEspeciales al
    // momento del submit. Lo dejamos vacío inicialmente; el template lee la
    // versión formateada via getter `horarioFormatted`.
    horario_atencion: '',
    descripcion: '',
    sitio_web: '',
    latitud: null as number | null,
    longitud: null as number | null,
  };

  // Horario estructurado. Índices 0..6 = Lun..Dom (orden semana ES).
  readonly DAYS_FULL = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  readonly DAYS_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  horarioBase = { start: '08:00', end: '18:00' };
  // Default: Lun-Sáb marcado, domingo no.
  diasMarcados: boolean[] = [true, true, true, true, true, true, false];
  // Override por día (null = usa horarioBase).
  horariosEspeciales: ({ start: string; end: string } | null)[] = [
    null, null, null, null, null, null, null,
  ];

  private map?: L.Map;

  constructor(
    private readonly specialtiesService: WorkshopSpecialtyService,
    private readonly vehicleTypes: VehicleTypeService,
    private readonly onboarding: OnboardingService,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit(): void {
    if (!sessionStorage.getItem('onboarding_token')) {
      this.router.navigate(['/planes']);
      return;
    }
    this.specialtiesService.getSpecialties().subscribe((items) => this.specialties = items);
    // Tipos de vehículo se cargan en paralelo. El servicio devuelve el catálogo
    // seedeado por el backend (15 categorías al momento de escribir esto).
    this.vehicleTypes.list().subscribe((items) => this.tiposVehiculo = items);
  }

  ngAfterViewInit(): void {
    if (!this.mapRef) return;
    // Init Leaflet sobre el div ya renderizado en DOM.
    this.map = L.map(this.mapRef.nativeElement, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      scrollWheelZoom: true,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.map);

    // El pin queda fijo en el centro del viewport via overlay HTML (ver
    // template: `.center-pin`). Mover el mapa equivale a "mover el pin",
    // así que tomamos `getCenter()` después de cada interacción del usuario.
    const syncCenter = (): void => {
      const center = this.map!.getCenter();
      this.taller.latitud = center.lat;
      this.taller.longitud = center.lng;
    };
    syncCenter();
    // `moveend` se dispara cuando termina drag / zoom / setView. Es la señal
    // estable a usar — `move` dispararía en cada frame del drag y es ruidoso.
    this.map.on('moveend', syncCenter);
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  useMyLocation(): void {
    if (!navigator.geolocation) {
      this.error = 'Tu navegador no soporta geolocalización.';
      return;
    }
    this.locating = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.locating = false;
        const { latitude, longitude } = pos.coords;
        // `setView` dispara `moveend` → el handler global sincroniza
        // taller.latitud/longitud sin que tengamos que duplicar lógica acá.
        this.map?.setView([latitude, longitude], 16);
      },
      (err) => {
        this.locating = false;
        this.error = `No se pudo obtener tu ubicación: ${err.message}`;
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  toggleDay(i: number): void {
    this.diasMarcados[i] = !this.diasMarcados[i];
    if (!this.diasMarcados[i]) {
      // Si el día se desmarca, eliminamos cualquier override personalizado
      // para que al volver a marcarlo herede el horarioBase actual.
      this.horariosEspeciales[i] = null;
    }
  }

  toggleEspecial(i: number): void {
    if (this.horariosEspeciales[i]) {
      this.horariosEspeciales[i] = null;
    } else {
      this.horariosEspeciales[i] = {
        start: this.horarioBase.start,
        end: this.horarioBase.end,
      };
    }
  }

  setEspecial(i: number, field: 'start' | 'end', value: string): void {
    const current = this.horariosEspeciales[i];
    if (!current) return;
    this.horariosEspeciales[i] = { ...current, [field]: value };
  }

  /**
   * Construye una representación legible compacta:
   *   "Lunes a Sábado 08:00–18:00, Domingo 07:00–14:00"
   * Agrupa días consecutivos que comparten el mismo rango horario para no
   * imprimir 7 líneas largas cuando la mayoría tiene el mismo horario.
   */
  get horarioFormatted(): string {
    type Range = { start: string; end: string };
    interface Entry { day: number; range: Range; }
    const entries: Entry[] = [];
    for (let i = 0; i < 7; i++) {
      if (!this.diasMarcados[i]) continue;
      entries.push({
        day: i,
        range: this.horariosEspeciales[i] ?? { ...this.horarioBase },
      });
    }
    if (!entries.length) return '';

    // Agrupar contiguos con mismo rango.
    const groups: { start: number; end: number; range: Range }[] = [];
    for (const entry of entries) {
      const last = groups.at(-1);
      if (last && last.end + 1 === entry.day &&
          last.range.start === entry.range.start &&
          last.range.end === entry.range.end) {
        last.end = entry.day;
      } else {
        groups.push({ start: entry.day, end: entry.day, range: entry.range });
      }
    }

    return groups.map((g) => {
      const label = g.start === g.end
        ? this.DAYS_FULL[g.start]
        : `${this.DAYS_FULL[g.start]} a ${this.DAYS_FULL[g.end]}`;
      return `${label} ${g.range.start}-${g.range.end}`;
    }).join(', ');
  }

  isSelected(id: number): boolean { return this.selectedSpecialtyIds.includes(id); }
  toggleSpecialty(id: number): void {
    this.selectedSpecialtyIds = this.isSelected(id)
      ? this.selectedSpecialtyIds.filter((item) => item !== id)
      : [...this.selectedSpecialtyIds, id];
  }

  isTipoSelected(id: number): boolean { return this.selectedTipoVehiculoIds.includes(id); }
  toggleTipoVehiculo(id: number): void {
    this.selectedTipoVehiculoIds = this.isTipoSelected(id)
      ? this.selectedTipoVehiculoIds.filter((item) => item !== id)
      : [...this.selectedTipoVehiculoIds, id];
  }

  submit(): void {
    const token = sessionStorage.getItem('onboarding_token');
    if (!token) return;
    if (this.taller.latitud == null || this.taller.longitud == null) {
      this.error = 'Selecciona la ubicación del taller en el mapa.';
      return;
    }

    const horarioStr = this.horarioFormatted;
    if (!horarioStr) {
      this.error = 'Marca al menos un día de atención.';
      return;
    }
    // Backend recibe `horario_atencion` como string libre; serializamos la
    // forma estructurada (días + rangos + especiales) aquí.
    this.taller.horario_atencion = horarioStr;

    const fullName = `${this.adminFirstName.trim()} ${this.adminLastName.trim()}`.trim();
    // Username derivado del email: parte local sanitizada. Backend lo requiere
    // único pero invisible para el usuario.
    const username = this.usernameFromEmail(this.admin.email);

    this.loading = true;
    this.error = '';
    this.onboarding.createWorkshop({
      onboarding_token: token,
      admin: {
        username,
        email: this.admin.email,
        full_name: fullName,
        password: this.admin.password,
      },
      taller: {
        ...this.taller,
        especialidad_ids: this.selectedSpecialtyIds,
        tipo_vehiculo_ids: this.selectedTipoVehiculoIds,
      },
    }).subscribe({
      next: (response) => {
        sessionStorage.removeItem('onboarding_token');
        sessionStorage.removeItem('onboarding_plan');
        this.auth.persistExternalSession(response);
        this.router.navigate(['/taller']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo crear el taller.';
      },
    });
  }

  private usernameFromEmail(email: string): string {
    const localPart = email.split('@')[0] || 'usuario';
    const sanitized = localPart.replace(/[^a-zA-Z0-9_]/g, '');
    const safe = sanitized || 'usuario';
    // Sufijo numérico corto para evitar colisiones cuando dos personas
    // registran con el mismo prefijo de email en distintos dominios.
    return `${safe}${Date.now() % 100000}`;
  }
}
