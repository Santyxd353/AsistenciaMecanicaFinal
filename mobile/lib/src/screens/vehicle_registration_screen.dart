import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

class VehicleRegistrationScreen extends StatefulWidget {
  const VehicleRegistrationScreen({super.key});

  @override
  State<VehicleRegistrationScreen> createState() =>
      _VehicleRegistrationScreenState();
}

class _VehicleRegistrationScreenState extends State<VehicleRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _plateController = TextEditingController();
  final _brandController = TextEditingController();
  final _modelController = TextEditingController();
  final _yearController = TextEditingController();
  final _colorController = TextEditingController();

  final List<String> _aiPhotos = [];
  VehiclePhotoPreview? _aiPreview;
  bool _aiLoading = false;
  String? _aiError;

  @override
  void dispose() {
    _plateController.dispose();
    _brandController.dispose();
    _modelController.dispose();
    _yearController.dispose();
    _colorController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: controller.refreshData,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
            children: [
              const _HeaderCard(),
              const SizedBox(height: 16),
              _IaCard(
                photos: _aiPhotos,
                preview: _aiPreview,
                loading: _aiLoading,
                error: _aiError,
                onPickPhotos: _pickPhotos,
                onAnalyze: () => _analyzePhotos(controller),
                onClear: _clearAi,
                onApply: _applyPreviewToForm,
              ),
              const SizedBox(height: 16),
              _VehicleFormCard(
                formKey: _formKey,
                plateController: _plateController,
                brandController: _brandController,
                modelController: _modelController,
                yearController: _yearController,
                colorController: _colorController,
                loading: controller.loading,
                onSubmit: () => _submit(controller),
              ),
              const SizedBox(height: 16),
              _VehiclesList(vehicles: controller.vehicles),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pickPhotos() async {
    // Permitimos hasta 3 fotos: una vista lateral, plate, interior — más
    // que eso no aporta confianza adicional al LLM y aumenta payload Groq.
    final picker = ImagePicker();
    try {
      final picks = await picker.pickMultiImage(
        imageQuality: 88,
        maxWidth: 1600,
      );
      if (picks.isEmpty) {
        return;
      }
      setState(() {
        _aiPhotos
          ..clear()
          ..addAll(picks.take(3).map((x) => x.path));
        _aiPreview = null;
        _aiError = null;
      });
    } catch (error) {
      setState(() {
        _aiError = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _analyzePhotos(AppController controller) async {
    if (_aiPhotos.isEmpty) {
      setState(() => _aiError = 'Selecciona al menos una foto del vehiculo.');
      return;
    }
    setState(() {
      _aiLoading = true;
      _aiError = null;
    });
    try {
      final preview = await controller.previewVehicleFromPhotos(_aiPhotos);
      setState(() => _aiPreview = preview);
    } catch (error) {
      setState(() {
        _aiError = error.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _aiLoading = false);
      }
    }
  }

  void _applyPreviewToForm() {
    final preview = _aiPreview;
    if (preview == null) return;
    setState(() {
      if (preview.placa.trim().isNotEmpty) {
        _plateController.text = preview.placa.trim().toUpperCase();
      }
      if (preview.marca.trim().isNotEmpty) {
        _brandController.text = preview.marca.trim();
      }
      if (preview.modelo.trim().isNotEmpty) {
        _modelController.text = preview.modelo.trim();
      }
      if (preview.anio != null) {
        _yearController.text = preview.anio.toString();
      }
      if (preview.color.trim().isNotEmpty) {
        _colorController.text = preview.color.trim();
      }
    });
    _showMessage('Datos sugeridos por IA aplicados. Revisa antes de guardar.');
  }

  void _clearAi() {
    setState(() {
      _aiPhotos.clear();
      _aiPreview = null;
      _aiError = null;
    });
  }

  Future<void> _submit(AppController controller) async {
    FocusScope.of(context).unfocus();
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    final yearText = _yearController.text.trim();
    final parsedYear = yearText.isEmpty ? null : int.tryParse(yearText);
    if (yearText.isNotEmpty && parsedYear == null) {
      _showMessage('El ano debe ser numerico.');
      return;
    }

    try {
      await controller.addVehicle(
        placa: _plateController.text,
        marca: _brandController.text,
        modelo: _modelController.text,
        anio: parsedYear,
        color: _colorController.text,
        // Primera foto IA se reutiliza como foto del vehiculo (si hubo).
        photoPath: _aiPhotos.isNotEmpty ? _aiPhotos.first : null,
      );
      if (!mounted) {
        return;
      }
      _plateController.clear();
      _brandController.clear();
      _modelController.clear();
      _yearController.clear();
      _colorController.clear();
      _clearAi();
      _showMessage('Vehiculo registrado correctamente.');
    } catch (error) {
      _showMessage(error.toString().replaceFirst('Exception: ', ''));
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard();

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      duration: const Duration(milliseconds: 420),
      curve: Curves.easeOutCubic,
      tween: Tween(begin: 0, end: 1),
      builder: (context, value, child) {
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, 18 * (1 - value)),
            child: child,
          ),
        );
      },
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFF322214),
          borderRadius: BorderRadius.circular(26),
          boxShadow: const [
            BoxShadow(
              color: Color(0x26715A3E),
              blurRadius: 24,
              offset: Offset(0, 12),
            ),
          ],
        ),
        child: const Padding(
          padding: EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'MIS VEHICULOS',
                style: TextStyle(
                  color: Color(0xFFEBD8C5),
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 2,
                ),
              ),
              SizedBox(height: 12),
              Text(
                'Registra tu auto con ayuda de IA',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  height: 1.08,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 12),
              Text(
                'Toma fotos del vehiculo y la IA sugiere placa, marca, modelo, ano y color. '
                'Tu siempre puedes corregirlo antes de guardar.',
                style: TextStyle(color: Color(0xFFEBD8C5), height: 1.45),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Card para subir fotos + analizar con IA + aplicar al formulario.
class _IaCard extends StatelessWidget {
  const _IaCard({
    required this.photos,
    required this.preview,
    required this.loading,
    required this.error,
    required this.onPickPhotos,
    required this.onAnalyze,
    required this.onClear,
    required this.onApply,
  });

  final List<String> photos;
  final VehiclePhotoPreview? preview;
  final bool loading;
  final String? error;
  final VoidCallback onPickPhotos;
  final VoidCallback onAnalyze;
  final VoidCallback onClear;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) {
    final hasPhotos = photos.isNotEmpty;
    final hasPreview = preview != null;
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: Color(0xFFD2C4BB)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Sugerencia automatica (IA)',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                ),
                if (hasPhotos)
                  TextButton.icon(
                    onPressed: loading ? null : onClear,
                    icon: const Icon(Icons.close, size: 16),
                    label: const Text('Limpiar'),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Toma 1 a 3 fotos del vehiculo (frontal, lateral, placa). La IA '
              'leera placa y reconocera marca/modelo/color para autocompletar.',
              style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: loading ? null : onPickPhotos,
                icon: const Icon(Icons.add_photo_alternate_outlined),
                label: Text(
                  hasPhotos
                      ? '${photos.length} foto(s) listas — cambiar'
                      : 'Tomar / elegir fotos',
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF322214),
                  side: const BorderSide(color: Color(0xFFD2C4BB)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: (loading || !hasPhotos) ? null : onAnalyze,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF8D5524),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                icon: loading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.auto_awesome),
                label: Text(loading ? 'Analizando con IA...' : 'Analizar con IA'),
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFCE8E8),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE3B7B7)),
                ),
                child: Text(
                  error!,
                  style: const TextStyle(color: Color(0xFF8C2A2A)),
                ),
              ),
            ],
            if (hasPreview) ...[
              const SizedBox(height: 14),
              _PreviewBlock(preview: preview!, onApply: onApply),
            ],
          ],
        ),
      ),
    );
  }
}

class _PreviewBlock extends StatelessWidget {
  const _PreviewBlock({required this.preview, required this.onApply});

  final VehiclePhotoPreview preview;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) {
    final rows = <_PreviewRow>[
      _PreviewRow('Placa', preview.placa.isEmpty ? 'no detectada' : preview.placa),
      _PreviewRow('Marca', preview.marca.isEmpty ? 'no detectada' : preview.marca),
      _PreviewRow('Modelo', preview.modelo.isEmpty ? 'no detectado' : preview.modelo),
      _PreviewRow('Ano', preview.anio?.toString() ?? 'no detectado'),
      _PreviewRow('Color', preview.color.isEmpty ? 'no detectado' : preview.color),
    ];
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF1E8DC),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFD2C4BB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, size: 18, color: Color(0xFF8D5524)),
              const SizedBox(width: 6),
              const Expanded(
                child: Text(
                  'Resultado de la IA',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
              ),
              Text(
                'fuente: ${preview.source}',
                style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF6F655B),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...rows,
          if (preview.resumen.trim().isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              preview.resumen,
              style: const TextStyle(
                color: Color(0xFF6F655B),
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
            ),
          ],
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: onApply,
              icon: const Icon(Icons.check),
              label: const Text('Usar estos datos en el formulario'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF322214),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PreviewRow extends StatelessWidget {
  const _PreviewRow(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 70,
            child: Text(
              label,
              style: const TextStyle(
                color: Color(0xFF6F655B),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }
}

class _VehicleFormCard extends StatelessWidget {
  const _VehicleFormCard({
    required this.formKey,
    required this.plateController,
    required this.brandController,
    required this.modelController,
    required this.yearController,
    required this.colorController,
    required this.loading,
    required this.onSubmit,
  });

  final GlobalKey<FormState> formKey;
  final TextEditingController plateController;
  final TextEditingController brandController;
  final TextEditingController modelController;
  final TextEditingController yearController;
  final TextEditingController colorController;
  final bool loading;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: Color(0xFFD2C4BB)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Form(
          key: formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Datos del vehiculo',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 14),
              _RutaField(
                controller: plateController,
                label: 'Placa',
                hint: 'ABC-123',
                textCapitalization: TextCapitalization.characters,
                validator: _required,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _RutaField(
                      controller: brandController,
                      label: 'Marca',
                      hint: 'Toyota',
                      validator: _required,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _RutaField(
                      controller: modelController,
                      label: 'Modelo',
                      hint: 'Corolla',
                      validator: _required,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _RutaField(
                      controller: yearController,
                      label: 'Ano',
                      hint: '2020',
                      keyboardType: TextInputType.number,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _RutaField(
                      controller: colorController,
                      label: 'Color',
                      hint: 'Blanco',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                height: 54,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF322214),
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: const Color(0xFFC0A78E),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(18),
                    ),
                  ),
                  onPressed: loading ? null : onSubmit,
                  icon: loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.directions_car_filled_outlined),
                  label: Text(loading ? 'Guardando...' : 'Registrar vehiculo'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String? _required(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Campo obligatorio';
    }
    return null;
  }
}

class _RutaField extends StatelessWidget {
  const _RutaField({
    required this.controller,
    required this.label,
    required this.hint,
    this.keyboardType,
    this.textCapitalization = TextCapitalization.words,
    this.validator,
  });

  final TextEditingController controller;
  final String label;
  final String hint;
  final TextInputType? keyboardType;
  final TextCapitalization textCapitalization;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      textCapitalization: textCapitalization,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        filled: true,
        fillColor: const Color(0xFFFFF9EF),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFD2C4BB)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFD2C4BB)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFF8D5524), width: 1.5),
        ),
      ),
    );
  }
}

class _VehiclesList extends StatelessWidget {
  const _VehiclesList({required this.vehicles});

  final List<Vehicle> vehicles;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: Color(0xFFD2C4BB)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Registrados',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                  ),
                ),
                Text(
                  '${vehicles.length}',
                  style: const TextStyle(
                    color: Color(0xFF8D5524),
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (vehicles.isEmpty)
              const _EmptyVehicleState()
            else
              ...vehicles.map(
                (vehicle) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _VehicleTile(vehicle: vehicle),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _EmptyVehicleState extends StatelessWidget {
  const _EmptyVehicleState();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF9EF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE5D8C9)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.directions_car_outlined, color: Color(0xFF8D5524)),
          SizedBox(height: 10),
          Text(
            'Aun no tienes vehiculos.',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          SizedBox(height: 6),
          Text(
            'Completa el formulario de arriba para poder reportar emergencias.',
            style: TextStyle(color: Color(0xFF6F655B), height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _VehicleTile extends StatelessWidget {
  const _VehicleTile({required this.vehicle});

  final Vehicle vehicle;

  @override
  Widget build(BuildContext context) {
    final details = [
      '${vehicle.marca} ${vehicle.modelo}'.trim(),
      if (vehicle.anio != null) vehicle.anio.toString(),
      if (vehicle.color.trim().isNotEmpty) vehicle.color.trim(),
    ].where((item) => item.trim().isNotEmpty).join(' - ');

    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFFFF9EF),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE5D8C9)),
      ),
      child: ListTile(
        leading: const CircleAvatar(
          backgroundColor: Color(0xFFEBD8C5),
          foregroundColor: Color(0xFF322214),
          child: Icon(Icons.directions_car_filled_outlined),
        ),
        title: Text(
          vehicle.placa,
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        subtitle: Text(
          details.isEmpty ? 'Vehiculo registrado' : details,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: const Icon(Icons.check_circle, color: Color(0xFF167B47)),
      ),
    );
  }
}
