import { CommonModule, isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  PLATFORM_ID,
  SimpleChanges,
  ViewChild,
  inject
} from '@angular/core';
import * as L from 'leaflet';

export type PuntoMapaTipo = 'incidente' | 'taller' | 'tecnico';

export interface PuntoMapaGeolocalizacion {
  latitud: number | null;
  longitud: number | null;
  etiqueta: string;
  tipo: PuntoMapaTipo;
}

@Component({
  selector: 'app-mapa-geolocalizacion',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './mapa-geolocalizacion.component.html',
  styleUrl: './mapa-geolocalizacion.component.css'
})
export class MapaGeolocalizacionComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() puntos: PuntoMapaGeolocalizacion[] = [];
  @Input() alto = '320px';

  @ViewChild('contenedorMapa') private contenedorMapa?: ElementRef<HTMLDivElement>;

  private readonly platformId = inject(PLATFORM_ID);
  private mapa: L.Map | null = null;
  private marcadores: L.CircleMarker[] = [];
  private ruta: L.Polyline | null = null;
  errorRenderMapa = false;

  get puntosValidos(): PuntoMapaGeolocalizacion[] {
    return this.puntos.filter((punto) => this.esPuntoValido(punto));
  }

  get tienePuntosValidos(): boolean {
    return this.puntosValidos.length > 0;
  }

  get etiquetaTipoMapa(): Record<PuntoMapaTipo, string> {
    return {
      incidente: 'Incidente',
      taller: 'Taller',
      tecnico: 'Técnico'
    };
  }

  ngAfterViewInit(): void {
    this.inicializarMapa();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['puntos'] && this.mapa) {
      this.actualizarUbicaciones();
    }
  }

  ngOnDestroy(): void {
    this.ruta?.remove();
    this.ruta = null;
    if (this.mapa) {
      this.mapa.remove();
      this.mapa = null;
    }
  }

  private inicializarMapa(): void {
    if (!isPlatformBrowser(this.platformId) || !this.contenedorMapa?.nativeElement || this.mapa) {
      return;
    }

    try {
      const centroInicial: L.LatLngExpression = this.coordenadasValidas
        ? [this.puntosValidos[0].latitud as number, this.puntosValidos[0].longitud as number]
        : [-16.5, -68.15];

      this.mapa = L.map(this.contenedorMapa.nativeElement, {
        zoomControl: true,
        attributionControl: true
      }).setView(centroInicial, this.tienePuntosValidos ? 15 : 5);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(this.mapa);

      this.errorRenderMapa = false;
      this.actualizarUbicaciones();
      this.programarAjusteMapa();
    } catch {
      this.errorRenderMapa = true;
      if (this.mapa) {
        this.mapa.remove();
        this.mapa = null;
      }
    }
  }

  private get coordenadasValidas(): boolean {
    return this.tienePuntosValidos;
  }

  private actualizarUbicaciones(): void {
    if (!this.mapa || !this.tienePuntosValidos) {
      return;
    }

    try {
      this.marcadores.forEach((marcador) => marcador.remove());
      this.marcadores = [];
      this.ruta?.remove();
      this.ruta = null;

      const bounds = L.latLngBounds([]);

      this.puntosValidos.forEach((punto) => {
        const coordenadas: L.LatLngExpression = [punto.latitud as number, punto.longitud as number];
        const estilo = this.obtenerEstiloMarcador(punto.tipo);

        const marcador = L.circleMarker(coordenadas, estilo).addTo(this.mapa as L.Map);
        marcador.bindPopup(punto.etiqueta);
        this.marcadores.push(marcador);
        bounds.extend(L.latLng(punto.latitud as number, punto.longitud as number));
      });

      const rutaPuntos = this.puntosValidos
        .filter((punto) => punto.tipo !== 'incidente')
        .concat(this.puntosValidos.filter((punto) => punto.tipo === 'incidente'))
        .map((punto) => [punto.latitud as number, punto.longitud as number] as L.LatLngExpression);

      if (rutaPuntos.length >= 2) {
        this.ruta = L.polyline(rutaPuntos, {
          color: '#111827',
          weight: 4,
          opacity: 0.72,
          dashArray: '8 8',
        }).addTo(this.mapa as L.Map);
      }

      if (this.puntosValidos.length === 1) {
        const unico = this.puntosValidos[0];
        this.mapa.setView([unico.latitud as number, unico.longitud as number], 15);
      } else {
        this.mapa.fitBounds(bounds, { padding: [30, 30] });
      }

      this.errorRenderMapa = false;
      this.programarAjusteMapa();
    } catch {
      this.errorRenderMapa = true;
    }
  }

  private esPuntoValido(punto: PuntoMapaGeolocalizacion): boolean {
    return punto.latitud !== null
      && punto.longitud !== null
      && Number.isFinite(punto.latitud)
      && Number.isFinite(punto.longitud)
      && punto.latitud >= -90
      && punto.latitud <= 90
      && punto.longitud >= -180
      && punto.longitud <= 180;
  }

  private obtenerEstiloMarcador(tipo: PuntoMapaTipo): L.CircleMarkerOptions {
    const estilos: Record<PuntoMapaTipo, L.CircleMarkerOptions> = {
      incidente: {
        radius: 10,
        color: '#b65118',
        weight: 3,
        fillColor: '#d37627',
        fillOpacity: 0.9
      },
      taller: {
        radius: 9,
        color: '#1d4ed8',
        weight: 3,
        fillColor: '#3b82f6',
        fillOpacity: 0.9
      },
      tecnico: {
        radius: 9,
        color: '#0f766e',
        weight: 3,
        fillColor: '#14b8a6',
        fillOpacity: 0.9
      }
    };

    return estilos[tipo];
  }

  private programarAjusteMapa(): void {
    if (!isPlatformBrowser(this.platformId) || !this.mapa) {
      return;
    }

    window.requestAnimationFrame(() => this.mapa?.invalidateSize());
    window.setTimeout(() => this.mapa?.invalidateSize(), 0);
    window.setTimeout(() => this.mapa?.invalidateSize(), 150);
  }
}
