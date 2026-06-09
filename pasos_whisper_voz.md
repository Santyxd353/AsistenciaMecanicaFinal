# Guía de implementación de voz con IA usando Faster-Whisper

Proyecto objetivo: **asistencia vehicular**  
Arquitectura sugerida: **FastAPI + Angular + Flutter**  
Objetivo: permitir que un cliente grabe o suba audio desde web/móvil, enviarlo al backend, transcribirlo a texto y usar ese texto para registrar o complementar una emergencia vehicular.

---

## 1. ¿Qué es Faster-Whisper?

**Faster-Whisper** es una implementación optimizada de los modelos Whisper usando **CTranslate2**, un motor de inferencia rápido para modelos Transformer. Su objetivo es ejecutar transcripción de voz a texto con mejor rendimiento y menor consumo de memoria que la implementación original de OpenAI Whisper.

En la práctica, Faster-Whisper permite montar una funcionalidad de **speech-to-text local o en servidor propio**, sin necesidad de enviar el audio a OpenAI, Google, Azure u otra nube externa.

### Ventajas principales

- Puede ejecutarse localmente en el backend.
- No requiere pagar una API externa por cada audio.
- Permite usar CPU o GPU.
- Soporta cuantización, por ejemplo `int8`, para reducir consumo de memoria.
- Es útil para proyectos web, móviles y sistemas internos.
- Puede configurarse con modelos pequeños para desarrollo o modelos grandes para mayor precisión.

### Modelos recomendados

| Modelo | Uso recomendado | Consumo aproximado |
|---|---|---|
| `tiny` | Pruebas rápidas | Muy bajo |
| `base` | Desarrollo local ligero | Bajo |
| `small` | Buen equilibrio precisión/rendimiento | Medio |
| `medium` | Mejor precisión | Alto |
| `large-v3` | Máxima precisión | Muy alto, ideal con GPU |

Para tu app de asistencia vehicular, recomiendo iniciar con:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Si el servidor tiene pocos recursos, usar:

```env
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

---

## 2. Flujo general de la funcionalidad

```txt
Cliente web o móvil
        ↓
Graba audio de emergencia
        ↓
Envía archivo al backend FastAPI
        ↓
FastAPI guarda audio temporalmente
        ↓
Faster-Whisper transcribe el audio localmente
        ↓
Backend devuelve texto transcrito
        ↓
Sistema usa el texto para registrar emergencia
```

Ejemplo de audio del cliente:

> “Mi vehículo se quedó parado en la avenida Blanco Galindo, parece que se recalentó el motor.”

Resultado esperado:

```json
{
  "transcripcion": "Mi vehículo se quedó parado en la avenida Blanco Galindo, parece que se recalentó el motor.",
  "idioma": "es",
  "duracion": 8.4
}
```

---

## 3. Backend FastAPI

### 3.1. Instalar dependencias

En el backend:

```bash
pip install fastapi uvicorn python-multipart faster-whisper
```

También es recomendable instalar `ffmpeg`, porque muchos audios móviles llegan en formatos como `.m4a`, `.webm`, `.aac` u `.ogg`.

En Ubuntu/Linux:

```bash
sudo apt update
sudo apt install ffmpeg
```

En Windows, instalar FFmpeg y agregarlo al `PATH`.

---

### 3.2. Variables de entorno

Crear o actualizar el archivo `.env`:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
MAX_AUDIO_MB=25
```

Significado:

| Variable | Descripción |
|---|---|
| `WHISPER_MODEL` | Modelo usado por Faster-Whisper |
| `WHISPER_DEVICE` | `cpu` o `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8`, `float16`, `float32` |
| `MAX_AUDIO_MB` | Tamaño máximo permitido por archivo |

---

### 3.3. Servicio de transcripción

Crear archivo:

```txt
app/services/voice_service.py
```

Código sugerido:

```python
import os
from functools import lru_cache
from faster_whisper import WhisperModel


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    """
    Carga el modelo una sola vez para evitar recargarlo en cada petición.
    """
    return WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )


def transcribe_audio(file_path: str, language: str = "es") -> dict:
    model = get_whisper_model()

    segments, info = model.transcribe(
        file_path,
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    text_parts = []

    for segment in segments:
        text_parts.append(segment.text.strip())

    final_text = " ".join(text_parts).strip()

    return {
        "transcripcion": final_text,
        "idioma": info.language,
        "probabilidad_idioma": info.language_probability,
        "duracion": info.duration,
    }
```

---

### 3.4. Endpoint para recibir audio

Crear archivo:

```txt
app/api/voice_routes.py
```

Código sugerido:

```python
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.voice_service import transcribe_audio

router = APIRouter(prefix="/api/v1/voz", tags=["Voz IA"])

MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "25"))
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".aac"}


@router.post("/transcribir")
async def transcribir_audio(audio: UploadFile = File(...)):
    extension = os.path.splitext(audio.filename or "")[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato de audio no permitido. Use mp3, wav, m4a, webm, ogg o aac.",
        )

    content = await audio.read()

    max_bytes = MAX_AUDIO_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El audio supera el límite de {MAX_AUDIO_MB} MB.",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_audio:
            temp_audio.write(content)
            temp_path = temp_audio.name

        result = transcribe_audio(temp_path, language="es")
        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al transcribir audio: {str(exc)}",
        )

    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
```

---

### 3.5. Registrar rutas en FastAPI

En `main.py`:

```python
from fastapi import FastAPI
from app.api.voice_routes import router as voice_router

app = FastAPI(title="Asistencia Vehicular API")

app.include_router(voice_router)
```

Endpoint final:

```txt
POST /api/v1/voz/transcribir
```

---

## 4. Integración con registro de emergencia

La transcripción puede usarse de dos formas.

### Opción A: Transcribir primero y luego registrar emergencia

Flujo:

```txt
1. Cliente graba audio
2. Envía audio a /api/v1/voz/transcribir
3. Backend devuelve texto
4. Frontend muestra el texto al usuario
5. Usuario confirma
6. Se registra emergencia con descripción textual
```

Ventaja: el usuario puede revisar y corregir el texto.

---

### Opción B: Registrar emergencia directamente con audio

Endpoint sugerido:

```txt
POST /api/v1/emergencias/audio
```

Flujo:

```txt
1. Cliente graba audio
2. Envía audio, latitud, longitud y datos del vehículo
3. Backend transcribe audio
4. Backend crea emergencia con la transcripción
```

Ejemplo de respuesta:

```json
{
  "id": 31,
  "estado": "pendiente",
  "descripcion": "Mi vehículo se quedó parado, parece que se recalentó el motor.",
  "audio_url": null,
  "latitud": -17.3895,
  "longitud": -66.1568
}
```

---

## 5. Angular: grabar y enviar audio

### 5.1. Servicio Angular

Crear:

```txt
src/app/services/voice.service.ts
```

Código:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TranscriptionResponse {
  transcripcion: string;
  idioma: string;
  probabilidad_idioma: number;
  duracion: number;
}

@Injectable({
  providedIn: 'root'
})
export class VoiceService {
  private apiUrl = 'http://localhost:8000/api/v1/voz';

  constructor(private http: HttpClient) {}

  transcribirAudio(audioBlob: Blob): Observable<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'emergencia.webm');

    return this.http.post<TranscriptionResponse>(
      `${this.apiUrl}/transcribir`,
      formData
    );
  }
}
```

---

### 5.2. Componente Angular para grabar

Ejemplo básico:

```typescript
import { Component } from '@angular/core';
import { VoiceService } from '../../services/voice.service';

@Component({
  selector: 'app-voice-recorder',
  templateUrl: './voice-recorder.component.html'
})
export class VoiceRecorderComponent {
  private mediaRecorder?: MediaRecorder;
  private audioChunks: Blob[] = [];

  isRecording = false;
  transcription = '';
  errorMessage = '';

  constructor(private voiceService: VoiceService) {}

  async startRecording() {
    this.errorMessage = '';
    this.transcription = '';

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream);
    this.audioChunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      this.sendAudio(audioBlob);
      stream.getTracks().forEach(track => track.stop());
    };

    this.mediaRecorder.start();
    this.isRecording = true;
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
    }
  }

  private sendAudio(audioBlob: Blob) {
    this.voiceService.transcribirAudio(audioBlob).subscribe({
      next: (response) => {
        this.transcription = response.transcripcion;
      },
      error: (error) => {
        this.errorMessage = error.error?.detail || 'Error al transcribir audio';
      }
    });
  }
}
```

HTML:

```html
<div class="voice-box">
  <button *ngIf="!isRecording" (click)="startRecording()">
    Grabar emergencia
  </button>

  <button *ngIf="isRecording" (click)="stopRecording()">
    Detener grabación
  </button>

  <p *ngIf="isRecording">Grabando audio...</p>

  <div *ngIf="transcription">
    <h3>Texto detectado:</h3>
    <textarea [(ngModel)]="transcription" rows="5"></textarea>
  </div>

  <p class="error" *ngIf="errorMessage">{{ errorMessage }}</p>
</div>
```

---

## 6. Flutter: grabar y enviar audio

### 6.1. Dependencias

En `pubspec.yaml`:

```yaml
dependencies:
  record: ^6.1.1
  path_provider: ^2.1.5
  http: ^1.2.2
  permission_handler: ^11.3.1
```

Ejecutar:

```bash
flutter pub get
```

---

### 6.2. Permisos Android

En:

```txt
android/app/src/main/AndroidManifest.xml
```

Agregar:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
```

---

### 6.3. Servicio Flutter

Crear:

```txt
lib/services/voice_service.dart
```

Código:

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class VoiceService {
  final String baseUrl;

  VoiceService({required this.baseUrl});

  Future<Map<String, dynamic>> transcribirAudio(File audioFile) async {
    final uri = Uri.parse('$baseUrl/api/v1/voz/transcribir');

    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      await http.MultipartFile.fromPath('audio', audioFile.path),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Error ${response.statusCode}: ${response.body}');
  }
}
```

---

### 6.4. Pantalla Flutter básica

```dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import '../services/voice_service.dart';

class VoiceEmergencyPage extends StatefulWidget {
  const VoiceEmergencyPage({super.key});

  @override
  State<VoiceEmergencyPage> createState() => _VoiceEmergencyPageState();
}

class _VoiceEmergencyPageState extends State<VoiceEmergencyPage> {
  final AudioRecorder _recorder = AudioRecorder();

  late final VoiceService _voiceService;

  bool _isRecording = false;
  bool _isLoading = false;
  String _transcription = '';
  String _error = '';
  String? _audioPath;

  @override
  void initState() {
    super.initState();
    _voiceService = VoiceService(
      baseUrl: 'http://10.0.2.2:8000',
    );
  }

  Future<void> _startRecording() async {
    setState(() {
      _error = '';
      _transcription = '';
    });

    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      setState(() {
        _error = 'No se concedió permiso para usar el micrófono.';
      });
      return;
    }

    final directory = await getTemporaryDirectory();
    final filePath = '${directory.path}/emergencia_${DateTime.now().millisecondsSinceEpoch}.m4a';

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 128000,
        sampleRate: 44100,
      ),
      path: filePath,
    );

    setState(() {
      _audioPath = filePath;
      _isRecording = true;
    });
  }

  Future<void> _stopRecording() async {
    final path = await _recorder.stop();

    setState(() {
      _isRecording = false;
      _audioPath = path;
    });

    if (path != null) {
      await _sendAudio(File(path));
    }
  }

  Future<void> _sendAudio(File file) async {
    setState(() {
      _isLoading = true;
      _error = '';
    });

    try {
      final result = await _voiceService.transcribirAudio(file);
      setState(() {
        _transcription = result['transcripcion'] ?? '';
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergencia por voz'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ElevatedButton.icon(
              onPressed: _isLoading
                  ? null
                  : _isRecording
                      ? _stopRecording
                      : _startRecording,
              icon: Icon(_isRecording ? Icons.stop : Icons.mic),
              label: Text(_isRecording ? 'Detener grabación' : 'Grabar emergencia'),
            ),
            const SizedBox(height: 16),
            if (_isRecording)
              const Text('Grabando audio...', textAlign: TextAlign.center),
            if (_isLoading)
              const Center(child: CircularProgressIndicator()),
            if (_transcription.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text('Texto detectado:'),
              TextField(
                controller: TextEditingController(text: _transcription),
                maxLines: 5,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                ),
              ),
            ],
            if (_error.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                _error,
                style: const TextStyle(color: Colors.red),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

Notas importantes para Flutter:

- En emulador Android usar `http://10.0.2.2:8000` para acceder al backend local.
- En dispositivo físico usar la IP local de tu PC, por ejemplo `http://192.168.1.50:8000`.
- En producción usar HTTPS.

---

## 7. Configuración CORS en FastAPI

Si Angular o Flutter no pueden conectar al backend por CORS, agregar:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Para producción no usar `*` sin control. Configurar sólo dominios autorizados.

---

## 8. Seguridad y validaciones recomendadas

Implementar estas validaciones antes de llevar a producción:

1. Validar extensión del archivo.
2. Validar tamaño máximo del audio.
3. Validar duración máxima, por ejemplo 60 segundos.
4. Requerir autenticación del cliente.
5. Asociar la transcripción al usuario autenticado.
6. Guardar logs de errores sin exponer datos sensibles.
7. Eliminar archivos temporales después de transcribir.
8. Usar HTTPS en producción.
9. Limitar cantidad de solicitudes por usuario.
10. No guardar audios si no es necesario.

---

## 9. Estructura recomendada en FastAPI

```txt
backend/
└── app/
    ├── main.py
    ├── api/
    │   ├── voice_routes.py
    │   └── emergency_routes.py
    ├── services/
    │   └── voice_service.py
    ├── models/
    │   └── emergency.py
    ├── schemas/
    │   └── emergency_schema.py
    └── core/
        └── config.py
```

---

## 10. Integración sugerida con emergencia vehicular

Modelo de emergencia simplificado:

```python
class Emergencia(Base):
    __tablename__ = "emergencias"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, nullable=False)
    vehiculo_id = Column(Integer, nullable=True)
    descripcion = Column(Text, nullable=False)
    transcripcion_audio = Column(Text, nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    estado = Column(String, default="pendiente")
    created_at = Column(DateTime, default=datetime.utcnow)
```

Endpoint sugerido:

```txt
POST /api/v1/emergencias/audio
```

Campos enviados:

```txt
audio: archivo
vehiculo_id: int
latitud: float
longitud: float
```

Respuesta:

```json
{
  "id": 12,
  "estado": "pendiente",
  "descripcion": "Mi auto no enciende y estoy detenido cerca del puente.",
  "latitud": -17.3895,
  "longitud": -66.1568
}
```

---

## 11. Mejoras con IA después de transcribir

Después de obtener el texto, puedes aplicar reglas o IA adicional para clasificar el incidente.

Ejemplo básico sin IA externa:

```python
def clasificar_emergencia(texto: str) -> str:
    texto = texto.lower()

    if "llanta" in texto or "neumático" in texto or "pinch" in texto:
        return "neumatico"

    if "batería" in texto or "no enciende" in texto:
        return "bateria"

    if "motor" in texto or "recalent" in texto:
        return "motor"

    if "choque" in texto or "accidente" in texto:
        return "accidente"

    return "otro"
```

Resultado:

```json
{
  "transcripcion": "Mi auto no enciende, parece que es la batería.",
  "categoria_detectada": "bateria"
}
```

---

## 12. Pruebas con Postman

Método:

```txt
POST
```

URL:

```txt
http://localhost:8000/api/v1/voz/transcribir
```

Body:

```txt
form-data
key: audio
value: archivo .mp3/.wav/.m4a/.webm
```

Respuesta esperada:

```json
{
  "transcripcion": "Necesito ayuda, mi vehículo no enciende.",
  "idioma": "es",
  "probabilidad_idioma": 0.98,
  "duracion": 6.3
}
```

---

## 13. Problemas comunes

### Error: `ffmpeg not found`

Solución:

```bash
sudo apt install ffmpeg
```

En Windows, instalar FFmpeg y agregarlo al PATH.

---

### El primer audio tarda mucho

Es normal. La primera petición carga el modelo en memoria. Las siguientes peticiones serán más rápidas.

---

### El servidor consume mucha RAM

Usar modelo más pequeño:

```env
WHISPER_MODEL=base
```

O usar cuantización:

```env
WHISPER_COMPUTE_TYPE=int8
```

---

### Flutter no conecta al backend local

Si usas emulador Android:

```txt
http://10.0.2.2:8000
```

Si usas celular físico:

```txt
http://IP_DE_TU_PC:8000
```

Ejemplo:

```txt
http://192.168.1.50:8000
```

---

## 14. Recomendación final para tu proyecto

Para tu aplicación de asistencia vehicular, la mejor primera versión sería:

```txt
Flutter / Angular graban audio
        ↓
FastAPI recibe audio
        ↓
Faster-Whisper transcribe localmente
        ↓
Usuario revisa texto
        ↓
Se registra la emergencia
        ↓
Backend asigna estado pendiente
        ↓
Taller recibe la solicitud
```

Configuración inicial recomendada:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
MAX_AUDIO_MB=25
```

Si el servidor es débil:

```env
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Si en producción tienes GPU:

```env
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

---

## 15. Checklist de implementación

- [ ] Instalar `faster-whisper`.
- [ ] Instalar FFmpeg.
- [ ] Crear variables de entorno.
- [ ] Crear `voice_service.py`.
- [ ] Crear endpoint `/api/v1/voz/transcribir`.
- [ ] Probar endpoint con Postman.
- [ ] Crear servicio Angular.
- [ ] Crear componente Angular con `MediaRecorder`.
- [ ] Agregar permisos de micrófono en Flutter.
- [ ] Crear servicio Flutter para enviar audio.
- [ ] Crear pantalla Flutter de grabación.
- [ ] Conectar transcripción con registro de emergencia.
- [ ] Agregar validaciones de seguridad.
- [ ] Probar en local.
- [ ] Probar en dispositivo físico.
- [ ] Preparar configuración para producción.

---

## 16. Conclusión

Faster-Whisper es una buena opción para tu sistema porque permite implementar voz con IA de forma local o dentro de tu propio backend, reduciendo dependencia de servicios externos. Para una app de asistencia vehicular, esto es útil porque el usuario puede reportar emergencias rápidamente mediante audio, y el sistema puede convertirlo en texto para crear solicitudes más completas.

La arquitectura recomendada es mantener la transcripción en FastAPI y usar Angular/Flutter sólo para capturar y enviar el audio.
