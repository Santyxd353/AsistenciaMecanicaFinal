import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import {
  MechanicProfile,
  MechanicProfileService,
  MechanicRating,
} from '../core/mechanic-profile.service';

@Component({
  selector: 'app-mechanic-profile',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <main class="page">
      <a routerLink="/taller/tecnicos" class="back-link" *ngIf="showBackToWorkshop">← Volver al equipo</a>

      <ng-container *ngIf="loading">
        <p class="loading">Cargando perfil del mecánico...</p>
      </ng-container>

      <ng-container *ngIf="!loading && error">
        <div class="error">{{ error }}</div>
      </ng-container>

      <ng-container *ngIf="!loading && profile">
        <header class="hero">
          <div class="avatar" [class.placeholder]="!profile.foto_url">
            <img *ngIf="profile.foto_url" [src]="profile.foto_url" [alt]="profile.nombre">
            <span *ngIf="!profile.foto_url">{{ initials(profile.nombre) }}</span>
          </div>
          <div class="hero-body">
            <p class="overline">Perfil del mecánico</p>
            <h1>{{ profile.nombre }}</h1>
            <p class="taller" *ngIf="profile.taller_nombre">
              Taller: <strong>{{ profile.taller_nombre }}</strong>
            </p>

            <div class="rating-row">
              <div class="stars" [attr.aria-label]="profile.calificacion_promedio + ' de 5'">
                <span *ngFor="let star of [1,2,3,4,5]"
                      [class.filled]="star <= roundedStars(profile.calificacion_promedio)">★</span>
              </div>
              <span class="rating-value">{{ profile.calificacion_promedio.toFixed(1) }}</span>
              <span class="rating-count">({{ profile.total_calificaciones }} calificaciones)</span>
            </div>

            <div class="badges">
              <span class="badge" [class.green]="profile.disponible" [class.gray]="!profile.disponible">
                {{ profile.disponible ? 'Disponible' : 'Ocupado' }}
              </span>
              <span class="badge" [class.gray]="!profile.activo">
                {{ profile.activo ? 'Activo' : 'Inactivo' }}
              </span>
              <span class="badge gray">
                {{ profile.total_servicios_finalizados }} servicios finalizados
              </span>
            </div>
          </div>
        </header>

        <section class="card">
          <h2>Especialidades</h2>
          <div class="specialties" *ngIf="profile.especialidades.length; else noSpec">
            <span class="chip" *ngFor="let e of profile.especialidades">{{ e.nombre }}</span>
          </div>
          <ng-template #noSpec>
            <p class="hint">Este mecánico aún no tiene especialidades asignadas.</p>
          </ng-template>
        </section>

        <section class="card">
          <h2>Calificaciones recientes</h2>
          <p class="hint" *ngIf="!ratings.length">
            Todavía no hay calificaciones para este mecánico.
            Las calificaciones se generan después de finalizar un servicio.
          </p>
          <article class="rating" *ngFor="let r of ratings">
            <header>
              <div class="stars small">
                <span *ngFor="let star of [1,2,3,4,5]" [class.filled]="star <= r.puntaje">★</span>
              </div>
              <strong>{{ r.cliente_nombre || 'Cliente' }}</strong>
              <span class="date">{{ r.fecha_creacion | date:'dd/MM/yyyy' }}</span>
            </header>
            <p *ngIf="r.comentario">{{ r.comentario }}</p>
          </article>
        </section>
      </ng-container>
    </main>
  `,
  styles: [`
    :host { display:block; min-height:100vh; background:#f5efe7; color:#2f241d;
            font-family:Inter,Segoe UI,Arial,sans-serif; }
    .page { max-width: 920px; margin: 0 auto; padding: 32px 22px 60px; }
    .back-link { display:inline-block; color:#8b5e34; text-decoration:none;
                 font-weight:700; margin-bottom:14px; }
    .back-link:hover { text-decoration:underline; }
    .loading,.hint { color:#7a6554; }
    .error { background:#fee2e2; color:#991b1b; padding:14px; border-radius:12px; }

    .hero { display:flex; gap:22px; align-items:center; background:#fff;
            border:1px solid #ead7c4; border-radius:20px; padding:24px;
            box-shadow:0 18px 48px rgba(86,52,28,.08); margin-bottom:18px; }
    .avatar { width:104px; height:104px; border-radius:50%; overflow:hidden;
              background:#fff8ef; border:2px solid #ead7c4; flex:0 0 auto;
              display:flex; align-items:center; justify-content:center; }
    .avatar img { width:100%; height:100%; object-fit:cover; }
    .avatar.placeholder span { font-size:34px; font-weight:900; color:#8b5e34; }

    .hero-body { flex:1 1 auto; min-width:0; }
    .overline { text-transform:uppercase; letter-spacing:.14em; font-size:11px;
                font-weight:800; color:#8b5e34; margin:0 0 4px; }
    h1 { margin:0; font-size:32px; line-height:1.1; }
    .taller { margin:6px 0 12px; color:#5c4a3a; }
    .badges { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .badge { padding:5px 10px; border-radius:999px; font-size:12px;
             font-weight:800; background:#fff8ef; border:1px solid #ead7c4;
             color:#5c4a3a; }
    .badge.green { background:#dcfce7; border-color:#bbf7d0; color:#14532d; }
    .badge.gray { background:#f1efea; border-color:#d8d2c8; color:#6c5e4f; }

    .rating-row { display:flex; align-items:center; gap:10px; margin-top:4px; }
    .stars { display:inline-flex; color:#dcd2c2; font-size:20px; letter-spacing:1px; }
    .stars.small { font-size:14px; }
    .stars .filled { color:#f5a524; }
    .rating-value { font-weight:900; font-size:18px; }
    .rating-count { color:#7a6554; font-size:13px; }

    .card { background:#fff; border:1px solid #ead7c4; border-radius:18px;
            padding:22px; margin-bottom:14px;
            box-shadow:0 12px 32px rgba(86,52,28,.05); }
    .card h2 { margin:0 0 12px; font-size:18px; }
    .specialties { display:flex; gap:8px; flex-wrap:wrap; }
    .chip { background:#fff8ef; border:1px solid #ead7c4; padding:7px 12px;
            border-radius:999px; font-weight:700; font-size:13px; }

    .rating { padding:14px 0; border-top:1px solid #f1e8dc; }
    .rating:first-of-type { border-top:0; padding-top:6px; }
    .rating header { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
    .rating .date { margin-left:auto; color:#7a6554; font-size:12px; }
    .rating p { margin:0; line-height:1.5; color:#3d2e22; }

    @media (max-width:640px) {
      .hero { flex-direction:column; text-align:center; }
      .hero-body { text-align:center; }
      .badges,.rating-row { justify-content:center; }
      h1 { font-size:26px; }
    }
  `],
})
export class MechanicProfileComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(MechanicProfileService);
  private readonly cdr = inject(ChangeDetectorRef);

  profile: MechanicProfile | null = null;
  ratings: MechanicRating[] = [];
  loading = true;
  error = '';
  // Solo mostrar "Volver al equipo" si el usuario actual es WORKSHOP/admin.
  // El cliente no tiene esa ruta. El detalle exacto del rol se evalúa
  // dejando el flag a `true` por simplicidad (ruta es protegida arriba).
  showBackToWorkshop = true;

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    const id = idParam ? Number(idParam) : NaN;
    if (!id || Number.isNaN(id)) {
      this.error = 'ID de mecánico inválido.';
      this.loading = false;
      return;
    }
    const fallbackTimer = window.setTimeout(() => {
      if (!this.loading) {
        return;
      }
      this.error = 'No se pudo cargar el perfil. Verifica tu sesion e intenta nuevamente.';
      this.loading = false;
      this.cdr.detectChanges();
    }, 10000);
    // Lanzamos perfil + ratings en paralelo. Si una de las llamadas falla,
    // forkJoin emite error → quedamos sin perfil ni ratings. Cargamos cada
    // una por separado para que un fallo parcial (p. ej. ratings 500) no
    // bloquee el render del perfil principal.
    this.service.getProfile(id).subscribe({
      next: (profile) => {
        window.clearTimeout(fallbackTimer);
        this.profile = {
          ...profile,
          especialidades: Array.isArray(profile.especialidades) ? profile.especialidades : [],
          calificacion_promedio: Number(profile.calificacion_promedio || 0),
          total_calificaciones: Number(profile.total_calificaciones || 0),
          total_servicios_finalizados: Number(profile.total_servicios_finalizados || 0),
        };
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        window.clearTimeout(fallbackTimer);
        // eslint-disable-next-line no-console
        console.error('[mechanic-profile] perfil error', err);
        this.error =
          err?.error?.detail ||
          err?.message ||
          `No se pudo cargar el perfil del mecánico (HTTP ${err?.status ?? '?'}).`;
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
    this.service.listRatings(id, 0, 20).subscribe({
      next: (ratings) => {
        this.ratings = Array.isArray(ratings) ? ratings : [];
        this.cdr.detectChanges();
      },
      error: (err) => {
        // eslint-disable-next-line no-console
        console.warn('[mechanic-profile] ratings error', err);
      },
    });
  }

  roundedStars(value: number): number {
    return Math.round(value);
  }

  initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join('');
  }
}
