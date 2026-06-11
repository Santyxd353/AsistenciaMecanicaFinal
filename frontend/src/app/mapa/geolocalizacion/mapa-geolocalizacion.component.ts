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
  private routeRequestSeq = 0;
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
      this.routeRequestSeq++;
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

      this.dibujarRutaOperativa();

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

  private dibujarRutaOperativa(): void {
    const incidente = this.puntosValidos.find((punto) => punto.tipo === 'incidente');
    const tecnico = this.puntosValidos.find((punto) => punto.tipo === 'tecnico');

    if (!this.mapa || !incidente || !tecnico) {
      return;
    }

    const fallback: L.LatLngExpression[] = [
      [tecnico.latitud as number, tecnico.longitud as number],
      [incidente.latitud as number, incidente.longitud as number],
    ];
    this.ruta = this.crearPolylineRuta(fallback, true);

    const seq = this.routeRequestSeq;
    this.obtenerRutaOsrm(tecnico, incidente)
      .then((rutaReal) => {
        if (!this.mapa || seq !== this.routeRequestSeq || rutaReal.length < 2) {
          return;
        }
        this.ruta?.remove();
        this.ruta = this.crearPolylineRuta(rutaReal, false);
      })
      .catch(() => {
        // Conserva la linea fallback si OSRM no responde.
      });
  }

  private crearPolylineRuta(points: L.LatLngExpression[], fallback: boolean): L.Polyline {
    return L.polyline(points, {
      color: fallback ? '#8a6a4f' : '#8D5524',
      weight: fallback ? 4 : 5,
      opacity: fallback ? 0.65 : 0.9,
      dashArray: fallback ? '8 8' : undefined,
    }).addTo(this.mapa as L.Map);
  }

  private async obtenerRutaOsrm(
    origen: PuntoMapaGeolocalizacion,
    destino: PuntoMapaGeolocalizacion,
  ): Promise<L.LatLngExpression[]> {
    const url = [
      'https://router.project-osrm.org/route/v1/driving/',
      `${origen.longitud},${origen.latitud};${destino.longitud},${destino.latitud}`,
      '?overview=full&geometries=geojson',
    ].join('');

    const response = await fetch(url);
    if (!response.ok) {
      return [];
    }
    const body = await response.json() as {
      routes?: Array<{ geometry?: { coordinates?: Array<[number, number]> } }>;
    };
    const coordinates = body.routes?.[0]?.geometry?.coordinates ?? [];
    return coordinates.map(([lng, lat]) => [lat, lng] as L.LatLngExpression);
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
