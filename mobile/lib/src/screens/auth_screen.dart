import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../models.dart';

enum _AuthMode {
  home,
  selection,
  registerChoice,
  client,
  admin,
  worker,
  workshopRegister,
  plans,
  onboarding,
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _workshopSearchController = TextEditingController();
  final _workshopNameController = TextEditingController();
  final _addressController = TextEditingController();
  final _phoneController = TextEditingController();
  final _scheduleController = TextEditingController(
    text: 'Lunes a domingo 08:00 - 20:00',
  );
  final _descriptionController = TextEditingController();

  // Onboarding workshop: ubicación seleccionada por el usuario tocando el mapa.
  // Default Santa Cruz. Si el usuario usa "Mi ubicación" se reemplaza. El pin
  // arranca pre-cargado en el centro para que siempre haya una ubicación
  // visible que enviar; el usuario puede moverlo tocando otro punto.
  static const LatLng _defaultMapCenter = LatLng(-17.7833, -63.1821);
  LatLng? _workshopPin = _defaultMapCenter;
  final MapController _workshopMapController = MapController();
  bool _locatingWorkshop = false;

  // ----- Horario estructurado del taller (UI nueva) -----
  // Días: 0=Lunes ... 6=Domingo. Por defecto abre Lun-Sáb.
  static const List<String> _diasFull = [
    'Lunes',
    'Martes',
    'Miércoles',
    'Jueves',
    'Viernes',
    'Sábado',
    'Domingo',
  ];
  final List<bool> _diasMarcados = [true, true, true, true, true, true, false];
  TimeOfDay _horarioBaseInicio = const TimeOfDay(hour: 8, minute: 0);
  TimeOfDay _horarioBaseFin = const TimeOfDay(hour: 18, minute: 0);
  // null = el día usa el horario base. Si no es null, override del día.
  final List<({TimeOfDay inicio, TimeOfDay fin})?> _horariosEspeciales =
      List.filled(7, null, growable: false);

  _AuthMode _mode = _AuthMode.home;
  bool _registerClient = false;
  String _error = '';
  PublicWorkshop? _selectedWorkshop;
  SaaSPlan? _selectedPlan;
  PlanPayment? _planPayment;

  @override
  void dispose() {
    _nameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _workshopSearchController.dispose();
    _workshopNameController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _scheduleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _mode == _AuthMode.home ? const Color(0xFFFFF9EF) : null,
      body: DecoratedBox(
        decoration: BoxDecoration(
          color: _mode == _AuthMode.home ? const Color(0xFFFFF9EF) : null,
          gradient: _mode == _AuthMode.home
              ? null
              : const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color(0xFF1B1713),
                    Color(0xFF5C2F16),
                    Color(0xFFF6EBDC),
                  ],
                ),
        ),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 280),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          child: _buildMode(context),
        ),
      ),
    );
  }

  Widget _buildMode(BuildContext context) {
    switch (_mode) {
      case _AuthMode.client:
        return _buildClientAccessFromStitch(context);
      case _AuthMode.selection:
        return _buildLoginSelectionFromStitch(context);
      case _AuthMode.registerChoice:
        return _buildRegisterChoiceFromStitch(context);
      case _AuthMode.admin:
        return _buildAdminAccessFromStitch(context);
      case _AuthMode.worker:
        return _buildWorkerAccessFromStitch(context);
      case _AuthMode.workshopRegister:
        return _buildWorkshopRegisterFromStitch(context);
      case _AuthMode.plans:
        return _buildPlansFromStitch(context);
      case _AuthMode.onboarding:
        return _buildOnboarding(context);
      case _AuthMode.home:
        return _buildHome(context);
    }
  }

  Widget _buildHome(BuildContext context) {
    return _HomeShell(
      key: const ValueKey('home'),
      child: SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: MediaQuery.sizeOf(context).height,
          ),
          child: Column(
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 18, 20, 10),
                child: _StitchLogo(),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 18,
                ),
                child: Column(
                  children: [
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 320),
                      child: const Text(
                        'Conecta conductores, talleres y mecánicos en tiempo real.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFF322214),
                          fontSize: 28,
                          height: 1.2,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 300),
                      child: const Text(
                        'Pide ayuda cuando tu auto falla, recibe respuesta de talleres cercanos y sigue la llegada del mecánico desde un solo lugar.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFF4E453E),
                          fontSize: 14,
                          height: 1.65,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Column(
                      children: [
                        _HeroButton(
                          label: 'Ver planes',
                          filled: true,
                          onPressed: () {
                            _go(_AuthMode.plans);
                            context.read<AppController>().loadPlans();
                          },
                        ),
                        const SizedBox(height: 12),
                        _HeroButton(
                          label: 'Ingresar',
                          onPressed: () => _go(_AuthMode.selection),
                        ),
                        const SizedBox(height: 12),
                        _HeroButton(
                          label: 'Registrarme',
                          onPressed: () => _go(_AuthMode.registerChoice),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 22, bottom: 16),
                child: _FeatureChipsScroller(),
              ),
              const _StitchDivider(),
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 16, 20, 20),
                child: _HomeStatsPanel(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLoginSelectionFromStitch(BuildContext context) {
    return Container(
      key: const ValueKey('selection-stitch'),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SafeArea(
        bottom: true,
        child: Column(
          children: [
            SizedBox(
              height: 56,
              child: Row(
                children: [
                  const SizedBox(width: 8),
                  IconButton(
                    tooltip: 'Volver',
                    onPressed: _backHome,
                    icon: const Icon(Icons.arrow_back),
                    color: const Color(0xFF322214),
                  ),
                  const Expanded(
                    child: Text(
                      '¿Qué usuario eres?',
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Color(0xFF322214),
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(width: 56),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
                physics: const BouncingScrollPhysics(),
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text(
                      'Selecciona el tipo de perfil con el que deseas ingresar a la plataforma RutaSOS.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFF4E453E),
                        fontSize: 14,
                        height: 1.42,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  _SelectionCard(
                    badge: 'US',
                    title: 'Login Usuarios',
                    description:
                        'Pide ayuda mecánica y gestiona tus vehículos.',
                    action: 'Entrar como cliente',
                    onTap: () => _go(_AuthMode.client),
                  ),
                  const SizedBox(height: 16),
                  _SelectionCard(
                    badge: 'AD',
                    title: 'Login Administrador',
                    description: 'Gestiona tu taller, solicitudes y personal.',
                    action: 'Ir al panel administrativo',
                    onTap: () => _go(_AuthMode.admin),
                  ),
                  const SizedBox(height: 16),
                  _SelectionCard(
                    badge: 'ME',
                    title: 'Login Trabajadores',
                    description:
                        'Recibe trabajos y actualiza tu disponibilidad.',
                    action: 'Entrar como trabajador',
                    onTap: () => _go(_AuthMode.worker),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildLoginSelection(BuildContext context) {
    return _LightScreen(
      key: const ValueKey('selection'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: _backHome,
                icon: const Icon(Icons.arrow_back),
              ),
              const SizedBox(width: 4),
              Text(
                '¿Qué usuario eres?',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
              ),
            ],
          ),
          const SizedBox(height: 22),
          const Center(
            child: Text(
              'Selecciona el tipo de perfil con el que deseas\ningresar a la plataforma RutaSOS.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF7A6556), height: 1.35),
            ),
          ),
          const SizedBox(height: 26),
          _SelectionCard(
            badge: 'US',
            title: 'Login Usuarios',
            description: 'Pide ayuda mecánica y gestiona tus vehículos.',
            action: 'Entrar como cliente',
            onTap: () => _go(_AuthMode.client),
          ),
          const SizedBox(height: 16),
          _SelectionCard(
            badge: 'AD',
            title: 'Login Administrador',
            description: 'Gestiona tu taller, solicitudes y personal.',
            action: 'Ir al panel administrativo',
            onTap: () => _go(_AuthMode.admin),
          ),
          const SizedBox(height: 16),
          _SelectionCard(
            badge: 'ME',
            title: 'Login Trabajadores',
            description: 'Recibe trabajos y actualiza tu disponibilidad.',
            action: 'Entrar como trabajador',
            onTap: () => _go(_AuthMode.worker),
          ),
        ],
      ),
    );
  }

  Widget _buildRegisterChoiceFromStitch(BuildContext context) {
    return Container(
      key: const ValueKey('register-choice'),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            SizedBox(
              height: 56,
              child: Row(
                children: [
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: _backHome,
                    icon: const Icon(Icons.arrow_back),
                    color: const Color(0xFF322214),
                  ),
                  const Expanded(
                    child: Text(
                      '¿Cómo quieres registrarte?',
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Color(0xFF322214),
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(width: 56),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 24),
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 10),
                    child: Text(
                      'Elige si vas a pedir asistencia como cliente o registrar tu taller en RutaSOS.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFF4E453E),
                        fontSize: 14,
                        height: 1.42,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  _SelectionCard(
                    badge: 'US',
                    title: 'Registrarme como usuario',
                    description:
                        'Crea tu cuenta para pedir auxilio y guardar vehículos.',
                    action: 'Crear cuenta de cliente',
                    onTap: () {
                      _registerClient = true;
                      _go(_AuthMode.client);
                    },
                  ),
                  const SizedBox(height: 16),
                  _SelectionCard(
                    badge: 'TA',
                    title: 'Registrar mi taller',
                    description:
                        'Crea tu cuenta, registra tu taller y luego elige un plan.',
                    action: 'Crear cuenta de taller',
                    onTap: () => _go(_AuthMode.workshopRegister),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClientAccessFromStitch(BuildContext context) {
    final controller = context.watch<AppController>();
    return _LoginUserStitchShell(
      key: const ValueKey('client-stitch'),
      onBack: _backHome,
      registerMode: _registerClient,
      onToggleRegister: () => setState(() {
        _registerClient = !_registerClient;
        _error = '';
      }),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_registerClient) ...[
              _stitchTextField(_nameController, 'Nombre completo'),
              const SizedBox(height: 18),
            ],
            _stitchTextField(
              _emailController,
              'Correo',
              hint: 'ejemplo@rutasos.com',
              icon: Icons.person_outline,
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 18),
            _stitchTextField(
              _passwordController,
              'Contraseña',
              hint: '••••••••',
              icon: Icons.lock_outline,
              suffixIcon: Icons.visibility_outlined,
              obscure: true,
            ),
            const SizedBox(height: 14),
            const Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Forgot Password?',
                style: TextStyle(
                  color: Color(0xFF715A3E),
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(height: 26),
            _stitchLoginButton(
              controller.loading
                  ? 'Entrando...'
                  : (_registerClient ? 'Crear cuenta' : 'Login'),
              controller.loading ? null : _submitClient,
            ),
            if (_error.isNotEmpty) _stitchError(_error),
          ],
        ),
      ),
    );
  }

  Widget _buildAdminAccessFromStitch(BuildContext context) {
    final controller = context.watch<AppController>();
    return _LoginAdminStitchShell(
      key: const ValueKey('admin-stitch'),
      onBack: _backHome,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _stitchTextField(
              _emailController,
              'Correo',
              hint: 'admin@rutasos.com',
              icon: Icons.person_outline,
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 18),
            _stitchTextField(
              _passwordController,
              'Contraseña',
              hint: '••••••••',
              icon: Icons.lock_outline,
              suffixIcon: Icons.visibility_outlined,
              obscure: true,
            ),
            const SizedBox(height: 18),
            const Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Forgot Password?',
                style: TextStyle(
                  color: Color(0xFF322214),
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(height: 24),
            _stitchLoginButton(
              controller.loading ? 'Entrando...' : 'Login',
              controller.loading ? null : _submitAdmin,
            ),
            if (_error.isNotEmpty) _stitchError(_error),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkerAccessFromStitch(BuildContext context) {
    final controller = context.watch<AppController>();
    if (controller.publicWorkshops.isEmpty && !controller.loading) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _mode == _AuthMode.worker) {
          context.read<AppController>().searchPublicWorkshops('');
        }
      });
    }
    return _LoginWorkerStitchShell(
      key: const ValueKey('worker-stitch'),
      onBack: _backHome,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _stitchTextField(
              _workshopSearchController,
              'Seleccionar Taller',
              hint:
                  _selectedWorkshop?.nombreComercial ??
                  'Elige tu centro de trabajo',
              suffixIcon: Icons.keyboard_arrow_down,
              onChanged: (value) {
                _selectedWorkshop = null;
                if (value.trim().length >= 2) {
                  controller.searchPublicWorkshops(value);
                }
              },
            ),
            const SizedBox(height: 10),
            if (_selectedWorkshop != null)
              Chip(
                backgroundColor: const Color(0xFFF9F3EA),
                avatar: const Icon(Icons.storefront_outlined, size: 18),
                label: Text(_selectedWorkshop!.nombreComercial),
                onDeleted: () => setState(() => _selectedWorkshop = null),
              )
            else if (controller.publicWorkshops.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text(
                  'Cargando talleres activos...',
                  style: TextStyle(color: Color(0xFF80756D), fontSize: 12),
                ),
              )
            else
              ...controller.publicWorkshops
                  .take(5)
                  .map(
                    (workshop) => ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: const CircleAvatar(
                        backgroundColor: Color(0xFF322214),
                        child: Icon(Icons.store, color: Colors.white, size: 17),
                      ),
                      title: Text(workshop.nombreComercial),
                      subtitle: Text(workshop.direccion),
                      onTap: () => setState(() => _selectedWorkshop = workshop),
                    ),
                  ),
            const SizedBox(height: 18),
            _stitchTextField(
              _usernameController,
              'Usuario asignado',
              hint: 'nombre@rutasos.com',
            ),
            const SizedBox(height: 18),
            _stitchTextField(
              _passwordController,
              'Contraseña',
              hint: '••••••••',
              suffixIcon: Icons.visibility_outlined,
              obscure: true,
            ),
            const SizedBox(height: 18),
            const Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Forgot Password?',
                style: TextStyle(
                  color: Color(0xFF715A3E),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(height: 24),
            _stitchLoginButton(
              controller.loading ? 'Entrando...' : 'Login',
              controller.loading ? null : _submitWorker,
            ),
            if (_error.isNotEmpty) _stitchError(_error),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkshopRegisterFromStitch(BuildContext context) {
    final controller = context.watch<AppController>();
    return _LoginUserStitchShell(
      key: const ValueKey('workshop-register'),
      onBack: () => _go(_AuthMode.registerChoice),
      registerMode: true,
      onToggleRegister: () => _go(_AuthMode.selection),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _stitchTextField(
              _nameController,
              'Nombre del administrador',
              hint: 'Tu nombre',
              icon: Icons.person_outline,
            ),
            const SizedBox(height: 18),
            _stitchTextField(
              _emailController,
              'Correo',
              hint: 'admin@taller.com',
              icon: Icons.alternate_email,
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 18),
            _stitchTextField(
              _passwordController,
              'Contraseña',
              hint: '••••••••',
              icon: Icons.lock_outline,
              suffixIcon: Icons.visibility_outlined,
              obscure: true,
            ),
            const SizedBox(height: 26),
            _stitchLoginButton(
              controller.loading ? 'Cargando planes...' : 'Continuar a planes',
              controller.loading ? null : _submitWorkshopPreRegister,
            ),
            if (_error.isNotEmpty) _stitchError(_error),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildClientAccess(BuildContext context) {
    final controller = context.watch<AppController>();
    return _FormShell(
      key: const ValueKey('client'),
      title: _registerClient ? 'Crear cuenta de usuario' : 'Login Usuarios',
      overline: 'Usuarios',
      subtitle: _registerClient
          ? 'Crea tu cuenta para reportar emergencias y guardar tus vehículos.'
          : 'Entra con tu correo para pedir auxilio y seguir tus solicitudes.',
      error: _error,
      onBack: _backHome,
      child: Form(
        key: _formKey,
        child: Column(
          children: [
            SegmentedButton<bool>(
              selected: {_registerClient},
              segments: const [
                ButtonSegment(value: false, label: Text('Ingresar')),
                ButtonSegment(value: true, label: Text('Registrarme')),
              ],
              onSelectionChanged: (value) {
                setState(() {
                  _registerClient = value.first;
                  _error = '';
                });
              },
            ),
            const SizedBox(height: 14),
            if (_registerClient) ...[
              _field(_nameController, 'Nombre completo'),
              const SizedBox(height: 12),
            ],
            _field(
              _emailController,
              'Correo',
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            _field(_passwordController, 'Contraseña', obscure: true),
            const SizedBox(height: 18),
            _submitButton(
              controller.loading
                  ? 'Entrando...'
                  : (_registerClient ? 'Crear cuenta' : 'Ingresar'),
              controller.loading ? null : _submitClient,
            ),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildAdminAccess(BuildContext context) {
    final controller = context.watch<AppController>();
    return _FormShell(
      key: const ValueKey('admin'),
      title: 'Login Administrador',
      overline: 'Administrativos',
      subtitle:
          'Acceso para administradores de taller. El panel super admin se usa solo desde PC.',
      error: _error,
      onBack: _backHome,
      child: Form(
        key: _formKey,
        child: Column(
          children: [
            _field(
              _emailController,
              'Correo',
              keyboard: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            _field(_passwordController, 'Contraseña', obscure: true),
            const SizedBox(height: 18),
            _submitButton(
              controller.loading ? 'Entrando...' : 'Entrar',
              controller.loading ? null : _submitAdmin,
            ),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildWorkerAccess(BuildContext context) {
    final controller = context.watch<AppController>();
    return _FormShell(
      key: const ValueKey('worker'),
      title: 'Login Trabajadores',
      overline: 'Trabajadores',
      subtitle: 'Busca tu taller y entra con el usuario que te asignaron.',
      error: _error,
      onBack: _backHome,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              controller: _workshopSearchController,
              decoration: const InputDecoration(
                labelText: 'Buscar taller',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: (value) {
                _selectedWorkshop = null;
                if (value.trim().length >= 2) {
                  controller.searchPublicWorkshops(value);
                }
              },
            ),
            const SizedBox(height: 10),
            if (_selectedWorkshop != null)
              Chip(
                avatar: const Icon(Icons.storefront_outlined, size: 18),
                label: Text(_selectedWorkshop!.nombreComercial),
                onDeleted: () => setState(() => _selectedWorkshop = null),
              )
            else
              ...controller.publicWorkshops.map(
                (workshop) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const CircleAvatar(child: Icon(Icons.store)),
                  title: Text(workshop.nombreComercial),
                  subtitle: Text(workshop.direccion),
                  onTap: () => setState(() => _selectedWorkshop = workshop),
                ),
              ),
            const SizedBox(height: 12),
            _field(_usernameController, 'Usuario del trabajador'),
            const SizedBox(height: 12),
            _field(_passwordController, 'Contraseña', obscure: true),
            const SizedBox(height: 18),
            _submitButton(
              controller.loading ? 'Entrando...' : 'Entrar como trabajador',
              controller.loading ? null : _submitWorker,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlansFromStitch(BuildContext context) {
    final controller = context.watch<AppController>();
    final plans = controller.plans.isEmpty ? _basePlans : controller.plans;

    return Container(
      key: const ValueKey('plans-stitch'),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Material(
            color: const Color(0xFFFFF9EF),
            elevation: 2,
            shadowColor: const Color(0x14322214),
            child: SafeArea(
              bottom: false,
              child: SizedBox(
                height: 64,
                child: Row(
                  children: [
                    IconButton(
                      onPressed: _backHome,
                      icon: const Icon(Icons.arrow_back),
                      color: const Color(0xFF322214),
                    ),
                    const Expanded(
                      child: Center(
                        child: Text(
                          'RutaSOS',
                          style: TextStyle(
                            color: Color(0xFF322214),
                            fontWeight: FontWeight.w800,
                            fontSize: 24,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 16, bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Text(
                      'PLANES SAAS',
                      style: TextStyle(
                        color: Color(0xFF715A3E),
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 2.4,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Text(
                      'Elige el plan para tu taller',
                      style: TextStyle(
                        color: Color(0xFF322214),
                        fontSize: 24,
                        height: 1.08,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Text(
                      'Cada plan controla administradores,\nmecánicos y capacidad de operación.',
                      style: TextStyle(
                        color: Color(0xFF4E453E),
                        fontSize: 13,
                        height: 1.3,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Expanded(
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      physics: const BouncingScrollPhysics(),
                      itemCount: plans.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 16),
                      itemBuilder: (context, index) {
                        final plan = plans[index];
                        return SizedBox(
                          width: MediaQuery.sizeOf(context).width * 0.82,
                          child: _StitchPlanCard(
                            plan: plan,
                            popular: plan.codigo == 'intermedio',
                            onTap: () => _openCheckout(plan),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 28),
                    child: Center(
                      child: Text(
                        'Mostrando planes base. El sistema actualizará estos datos desde el servidor cuando esté disponible.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFF80756D),
                          fontSize: 10,
                          height: 1.25,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openCheckout(SaaSPlan plan) async {
    setState(() {
      _selectedPlan = plan;
      _error = '';
    });
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.viewInsetsOf(sheetContext).bottom + 16,
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: const Color(0xFFFFF9EF),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: const Color(0xFFD2C4BB)),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x33322214),
                  blurRadius: 24,
                  offset: Offset(0, 12),
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Consumer<AppController>(
                builder: (context, controller, _) {
                  return Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Compra simulada',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: const Color(0xFF322214),
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Plan ${plan.nombre}. Después conectaremos Stripe.',
                        style: const TextStyle(
                          color: Color(0xFF4E453E),
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 18),
                      _field(_nameController, 'Tu nombre'),
                      const SizedBox(height: 12),
                      _field(
                        _emailController,
                        'Correo de contacto',
                        keyboard: TextInputType.emailAddress,
                      ),
                      if (_error.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Text(
                          _error,
                          style: const TextStyle(color: Color(0xFFB3261E)),
                        ),
                      ],
                      const SizedBox(height: 18),
                      _submitButton(
                        controller.loading
                            ? 'Confirmando...'
                            : 'Confirmar compra',
                        controller.loading
                            ? null
                            : () async {
                                await _simulatePurchase();
                                if (!sheetContext.mounted) return;
                                if (_mode == _AuthMode.onboarding) {
                                  Navigator.of(sheetContext).pop();
                                }
                              },
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }

  // ignore: unused_element
  Widget _buildPlans(BuildContext context) {
    final controller = context.watch<AppController>();
    final plans = controller.plans.isEmpty ? _basePlans : controller.plans;

    return _LightScreen(
      key: const ValueKey('plans'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: _backHome,
                icon: const Icon(Icons.arrow_back),
              ),
              const Expanded(
                child: Center(
                  child: Text(
                    'RutaSOS',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                  ),
                ),
              ),
              const SizedBox(width: 48),
            ],
          ),
          const Divider(height: 24, color: Color(0xFFEADCCB)),
          const Text(
            'PLANES RUTASOS',
            style: TextStyle(
              color: Color(0xFF8D5524),
              fontSize: 11,
              fontWeight: FontWeight.w900,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Elige el plan para tu taller',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: Colors.black,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Cada plan controla administradores,\nmecánicos y capacidad de operación.',
            style: TextStyle(color: Color(0xFF7A6556), height: 1.35),
          ),
          const SizedBox(height: 26),
          if (controller.loading && controller.plans.isEmpty)
            const Center(child: CircularProgressIndicator())
          else
            SizedBox(
              height: 390,
              child: PageView.builder(
                controller: PageController(viewportFraction: 0.88),
                padEnds: false,
                itemCount: plans.length,
                onPageChanged: (index) {
                  if (index >= 0 && index < plans.length) {
                    setState(() => _selectedPlan = plans[index]);
                  }
                },
                itemBuilder: (context, index) => Padding(
                  padding: const EdgeInsets.only(right: 14),
                  child: _PlanCard(
                    plan: plans[index],
                    selected:
                        _selectedPlan?.codigo == plans[index].codigo ||
                        (_selectedPlan == null && index == 0),
                    onTap: () => setState(() => _selectedPlan = plans[index]),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 16),
          const Center(
            child: Text(
              'Mostrando planes base. El sistema actualizará estos datos desde el servidor cuando esté disponible.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF9B8776), fontSize: 11),
            ),
          ),
          const SizedBox(height: 22),
          _field(_nameController, 'Tu nombre'),
          const SizedBox(height: 12),
          _field(
            _emailController,
            'Correo de contacto',
            keyboard: TextInputType.emailAddress,
          ),
          const SizedBox(height: 16),
          _submitButton(
            controller.loading ? 'Confirmando...' : 'Simular compra',
            controller.loading ? null : _simulatePurchase,
          ),
        ],
      ),
    );
  }

  static const List<SaaSPlan> _basePlans = [
    SaaSPlan(
      codigo: 'gratis',
      nombre: 'Gratis',
      descripcion: 'Plan inicial para validar un taller pequeño.',
      precioMensual: 0,
      maxAdministradores: 1,
      maxMecanicos: 5,
      maxSolicitudesMes: 30,
      beneficios: [
        '1 administrador',
        '5 mecánicos',
        '30 solicitudes al mes',
        'Dashboard básico',
        'Tracking en tiempo real',
      ],
    ),
    SaaSPlan(
      codigo: 'intermedio',
      nombre: 'Intermedio',
      descripcion: 'Operación diaria con más equipo y analítica.',
      precioMensual: 149,
      maxAdministradores: 3,
      maxMecanicos: 10,
      maxSolicitudesMes: 200,
      beneficios: [
        '3 administradores',
        '10 mecánicos',
        'KPIs operativos',
        'Historial avanzado',
        'Soporte por correo',
      ],
    ),
    SaaSPlan(
      codigo: 'premium',
      nombre: 'Premium',
      descripcion: 'Para talleres con alto volumen operativo.',
      precioMensual: 299,
      maxAdministradores: 10,
      maxMecanicos: 20,
      maxSolicitudesMes: 1000,
      beneficios: [
        '10 administradores',
        '20 mecánicos',
        'Dashboard avanzado',
        'Auditoría',
        'Reportes exportables',
      ],
    ),
    SaaSPlan(
      codigo: 'pro',
      nombre: 'Pro',
      descripcion: 'Escala completa sin límites de usuarios operativos.',
      precioMensual: 599,
      beneficios: [
        'Administradores ilimitados',
        'Mecánicos ilimitados',
        'Solicitudes ilimitadas',
        'Analítica avanzada',
        'Soporte premium',
      ],
    ),
  ];

  Widget _buildOnboarding(BuildContext context) {
    final controller = context.watch<AppController>();
    return _FormShell(
      key: const ValueKey('onboarding'),
      title: 'Crear taller',
      overline: _selectedPlan?.nombre ?? 'Plan confirmado',
      subtitle:
          'Completa los datos principales. Luego podrás agregar mecánicos y ajustar tu cuenta.',
      error: _error,
      onBack: () => _go(_AuthMode.plans),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Datos del administrador. Quitamos "Usuario" (lo derivamos del
            // email en submit) y separamos "Nombre completo" en Nombre y
            // Apellido para que el backend reciba `full_name = nombre apellido`.
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _field(_nameController, 'Nombre')),
                const SizedBox(width: 10),
                Expanded(child: _field(_lastNameController, 'Apellido')),
              ],
            ),
            const SizedBox(height: 12),
            _field(_workshopNameController, 'Nombre del taller'),
            const SizedBox(height: 12),
            _field(
              _passwordController,
              'Contraseña del administrador',
              obscure: true,
            ),
            const SizedBox(height: 12),
            _field(_addressController, 'Dirección'),
            const SizedBox(height: 12),
            _field(_phoneController, 'Teléfono', keyboard: TextInputType.phone),
            const SizedBox(height: 16),
            _buildHorarioPicker(),
            const SizedBox(height: 12),
            _field(_descriptionController, 'Descripción breve', maxLines: 2),
            const SizedBox(height: 16),
            _LocationLabel(
              pin: _workshopPin,
              locating: _locatingWorkshop,
              onUseMyLocation: _useMyWorkshopLocation,
            ),
            const SizedBox(height: 10),
            _buildWorkshopMap(),
            const SizedBox(height: 18),
            _submitButton(
              controller.loading
                  ? 'Creando taller...'
                  : 'Crear taller y entrar',
              controller.loading ? null : _submitOnboarding,
            ),
          ],
        ),
      ),
    );
  }

  /// UI estructurada para horarios: días marcados + horario base + override
  /// por día. Se serializa a string al momento del submit.
  Widget _buildHorarioPicker() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF9EF),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFD2C4BB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Horario de atención',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
          ),
          const SizedBox(height: 6),
          const Text(
            'Marca los días que abren. El horario base aplica a todos los marcados; '
            'activa "Personalizar" en un día para darle un horario especial.',
            style: TextStyle(
              color: Color(0xFF7A6554),
              height: 1.4,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 12),
          // Horario base.
          Row(
            children: [
              const Text(
                'Horario base',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              const Spacer(),
              _timeChip(_horarioBaseInicio, () => _pickBaseTime(true)),
              const SizedBox(width: 6),
              const Text('a'),
              const SizedBox(width: 6),
              _timeChip(_horarioBaseFin, () => _pickBaseTime(false)),
            ],
          ),
          const SizedBox(height: 10),
          // Lista de días.
          ...List.generate(7, (i) => _diaRow(i)),
          const SizedBox(height: 10),
          // Preview de la cadena formateada.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFF1E8DC),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              _horarioFormatted().isEmpty
                  ? 'Marca al menos un día.'
                  : 'Se mostrará como: ${_horarioFormatted()}',
              style: const TextStyle(
                color: Color(0xFF4D3A2C),
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _diaRow(int i) {
    final marcado = _diasMarcados[i];
    final special = _horariosEspeciales[i];
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 110,
            child: Row(
              children: [
                Checkbox(
                  value: marcado,
                  onChanged: (_) => setState(() {
                    _diasMarcados[i] = !marcado;
                    if (!_diasMarcados[i]) {
                      // Reset override al desmarcar el día para evitar
                      // estado huérfano.
                      _horariosEspeciales[i] = null;
                    }
                  }),
                ),
                Expanded(
                  child: Text(
                    _diasFull[i],
                    style: const TextStyle(fontWeight: FontWeight.w700),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          if (marcado) ...[
            const SizedBox(width: 4),
            InkWell(
              onTap: () => setState(() {
                if (special == null) {
                  _horariosEspeciales[i] = (
                    inicio: _horarioBaseInicio,
                    fin: _horarioBaseFin,
                  );
                } else {
                  _horariosEspeciales[i] = null;
                }
              }),
              child: Row(
                children: [
                  Icon(
                    special == null ? Icons.add_circle_outline : Icons.tune,
                    size: 16,
                    color: const Color(0xFF8B5E34),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    special == null ? 'Personalizar' : 'Especial',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF8B5E34),
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            if (special == null)
              Text(
                '${_fmtTod(_horarioBaseInicio)}–${_fmtTod(_horarioBaseFin)}',
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 12,
                  color: Color(0xFF6F655B),
                ),
              )
            else ...[
              _timeChip(special.inicio, () => _pickEspecialTime(i, true)),
              const SizedBox(width: 4),
              const Text('a', style: TextStyle(fontSize: 12)),
              const SizedBox(width: 4),
              _timeChip(special.fin, () => _pickEspecialTime(i, false)),
            ],
          ],
        ],
      ),
    );
  }

  Widget _timeChip(TimeOfDay tod, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFFD2C4BB)),
        ),
        child: Text(
          _fmtTod(tod),
          style: const TextStyle(
            fontFamily: 'monospace',
            fontSize: 12,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }

  String _fmtTod(TimeOfDay tod) =>
      '${tod.hour.toString().padLeft(2, '0')}:${tod.minute.toString().padLeft(2, '0')}';

  Future<void> _pickBaseTime(bool isStart) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: isStart ? _horarioBaseInicio : _horarioBaseFin,
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _horarioBaseInicio = picked;
      } else {
        _horarioBaseFin = picked;
      }
    });
  }

  Future<void> _pickEspecialTime(int i, bool isStart) async {
    final current = _horariosEspeciales[i];
    if (current == null) return;
    final picked = await showTimePicker(
      context: context,
      initialTime: isStart ? current.inicio : current.fin,
    );
    if (picked == null) return;
    setState(() {
      _horariosEspeciales[i] = (
        inicio: isStart ? picked : current.inicio,
        fin: isStart ? current.fin : picked,
      );
    });
  }

  /// Compone "Lunes a Sábado 08:00-18:00, Domingo 07:00-14:00" agrupando
  /// días contiguos con mismo rango.
  String _horarioFormatted() {
    final entries = <({int dia, String inicio, String fin})>[];
    for (var i = 0; i < 7; i++) {
      if (!_diasMarcados[i]) continue;
      final special = _horariosEspeciales[i];
      final inicio = special?.inicio ?? _horarioBaseInicio;
      final fin = special?.fin ?? _horarioBaseFin;
      entries.add((dia: i, inicio: _fmtTod(inicio), fin: _fmtTod(fin)));
    }
    if (entries.isEmpty) return '';
    final groups = <({int desde, int hasta, String inicio, String fin})>[];
    for (final entry in entries) {
      final last = groups.isEmpty ? null : groups.last;
      if (last != null &&
          last.hasta + 1 == entry.dia &&
          last.inicio == entry.inicio &&
          last.fin == entry.fin) {
        groups[groups.length - 1] = (
          desde: last.desde,
          hasta: entry.dia,
          inicio: last.inicio,
          fin: last.fin,
        );
      } else {
        groups.add((
          desde: entry.dia,
          hasta: entry.dia,
          inicio: entry.inicio,
          fin: entry.fin,
        ));
      }
    }
    return groups
        .map((g) {
          final label = g.desde == g.hasta
              ? _diasFull[g.desde]
              : '${_diasFull[g.desde]} a ${_diasFull[g.hasta]}';
          return '$label ${g.inicio}-${g.fin}';
        })
        .join(', ');
  }

  Widget _buildWorkshopMap() {
    final pin = _workshopPin;
    return SizedBox(
      height: 240,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          fit: StackFit.expand,
          children: [
            FlutterMap(
              mapController: _workshopMapController,
              options: MapOptions(
                initialCenter: pin ?? _defaultMapCenter,
                initialZoom: 13,
                // El pin vive en el overlay (Stack) anclado al centro del
                // viewport. Cuando el usuario mueve el mapa, sincronizamos
                // _workshopPin con `camera.center` para que el submit envíe
                // la coord apuntada por el pin estático.
                onPositionChanged: (camera, hasGesture) {
                  if (!mounted) return;
                  setState(() => _workshopPin = camera.center);
                },
              ),
              children: [
                TileLayer(
                  urlTemplate:
                      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'asistencia_mecanica_mobile',
                ),
              ],
            ),
            // Pin overlay: ancla en el centro horizontal y empuja la punta
            // del icono hacia la coordenada exacta del centro (alignment Y
            // negativa traslada el icono hacia arriba, dejando la "punta" del
            // pin justo en el centro geométrico del mapa).
            const Align(
              alignment: Alignment.center,
              child: FractionalTranslation(
                translation: Offset(0, -0.5),
                child: Icon(
                  Icons.location_pin,
                  color: Color(0xFF8B5E34),
                  size: 44,
                  shadows: [
                    Shadow(
                      color: Color(0x66000000),
                      blurRadius: 6,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
              ),
            ),
            // Sombra de referencia bajo el pin.
            const Align(
              alignment: Alignment.center,
              child: SizedBox(
                width: 12,
                height: 4,
                child: DecoratedBox(
                  decoration: ShapeDecoration(
                    color: Color(0x66000000),
                    shape: StadiumBorder(),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _useMyWorkshopLocation() async {
    setState(() {
      _locatingWorkshop = true;
      _error = '';
    });
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw Exception(
          'Activa el permiso de ubicación para detectar tu taller.',
        );
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 12),
        ),
      );
      final point = LatLng(position.latitude, position.longitude);
      setState(() => _workshopPin = point);
      _workshopMapController.move(point, 16);
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) setState(() => _locatingWorkshop = false);
    }
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    bool obscure = false,
    TextInputType? keyboard,
    int maxLines = 1,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboard,
      maxLines: obscure ? 1 : maxLines,
      cursorColor: const Color(0xFF322214),
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: const Color(0xFFFFF9EF),
        labelStyle: const TextStyle(color: Color(0xFF715A3E)),
        floatingLabelStyle: const TextStyle(
          color: Color(0xFF322214),
          fontWeight: FontWeight.w800,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFD2C4BB)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF322214), width: 1.6),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFBA1A1A)),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFBA1A1A), width: 1.6),
        ),
      ),
      validator: (value) {
        final text = value?.trim() ?? '';
        if (text.isEmpty) return 'Este campo es obligatorio.';
        if (label.toLowerCase().contains('correo') && !text.contains('@')) {
          return 'Ingresa un correo válido.';
        }
        if (label.toLowerCase().contains('contrase') && text.length < 6) {
          return 'Mínimo 6 caracteres.';
        }
        return null;
      },
    );
  }

  Widget _submitButton(String text, VoidCallback? onPressed) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFF322214),
          foregroundColor: Colors.white,
          disabledBackgroundColor: const Color(0xFFD2C4BB),
          disabledForegroundColor: const Color(0xFF80756D),
          shape: const StadiumBorder(),
          textStyle: const TextStyle(fontWeight: FontWeight.w800),
        ),
        onPressed: onPressed,
        child: Text(text),
      ),
    );
  }

  void _go(_AuthMode mode) {
    _formKey.currentState?.reset();
    setState(() {
      _mode = mode;
      _error = '';
    });
  }

  void _backHome() {
    setState(() {
      _mode = _AuthMode.home;
      _error = '';
      _selectedWorkshop = null;
    });
  }

  Future<void> _submitClient() async {
    if (!_formKey.currentState!.validate()) return;
    final controller = context.read<AppController>();
    try {
      if (_registerClient) {
        await controller.registerClient(
          username: _usernameFromEmail(_emailController.text),
          email: _emailController.text.trim(),
          fullName: _nameController.text.trim(),
          password: _passwordController.text,
        );
      } else {
        await controller.loginClient(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
      }
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _submitAdmin() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      await context.read<AppController>().loginAdmin(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _submitWorker() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedWorkshop == null) {
      setState(() => _error = 'Selecciona el taller donde trabajas.');
      return;
    }
    try {
      await context.read<AppController>().loginWorker(
        workshop: _selectedWorkshop!,
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _submitWorkshopPreRegister() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      await context.read<AppController>().loadPlans();
      if (!mounted) return;
      setState(() {
        _mode = _AuthMode.plans;
        _error = '';
      });
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _simulatePurchase() async {
    final planToBuy =
        _selectedPlan ??
        (context.read<AppController>().plans.isNotEmpty
            ? context.read<AppController>().plans.first
            : _basePlans.first);
    if (_nameController.text.trim().isEmpty ||
        !_emailController.text.trim().contains('@')) {
      setState(() => _error = 'Ingresa tu nombre y correo de contacto.');
      return;
    }
    try {
      final payment = await context.read<AppController>().simulatePlanPurchase(
        plan: planToBuy,
        email: _emailController.text.trim(),
        nombreContacto: _nameController.text.trim(),
      );
      setState(() {
        _planPayment = payment;
        _workshopNameController.text = '';
        _addressController.text = '';
        _phoneController.text = '';
        _mode = _AuthMode.onboarding;
        _error = '';
      });
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _submitOnboarding() async {
    if (!_formKey.currentState!.validate()) return;
    final token = _planPayment?.onboardingToken;
    if (token == null || token.isEmpty) {
      setState(() => _error = 'Primero confirma la compra simulada del plan.');
      return;
    }
    final pin = _workshopPin;
    if (pin == null) {
      setState(() => _error = 'Selecciona la ubicación del taller en el mapa.');
      return;
    }
    final horarioStr = _horarioFormatted();
    if (horarioStr.isEmpty) {
      setState(() => _error = 'Marca al menos un día de atención.');
      return;
    }
    // Backend solo conoce `full_name` (un único string). Concatenamos
    // nombre + apellido aquí para mantener la API intacta.
    final fullName = [
      _nameController.text.trim(),
      _lastNameController.text.trim(),
    ].where((s) => s.isNotEmpty).join(' ').trim();

    try {
      await context.read<AppController>().onboardWorkshop(
        onboardingToken: token,
        adminUsername: _usernameFromEmail(_emailController.text),
        adminEmail: _emailController.text.trim(),
        adminFullName: fullName,
        adminPassword: _passwordController.text,
        nombreComercial: _workshopNameController.text.trim(),
        direccion: _addressController.text.trim(),
        telefono: _phoneController.text.trim(),
        emailContacto: _emailController.text.trim(),
        horarioAtencion: horarioStr,
        especialidadIds: const [1],
        descripcion: _descriptionController.text.trim(),
        latitud: pin.latitude,
        longitud: pin.longitude,
      );
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    var message = error.toString().replaceFirst('Exception: ', '');
    if (message.contains('TimeoutException') ||
        message.contains('timed out') ||
        message.contains('Connection') ||
        message.contains('SocketException') ||
        message.contains('Failed host lookup')) {
      message =
          'No se pudo conectar al servidor. En telefono fisico ejecuta la app con API_BASE_URL=http://192.168.0.3:8000 y verifica que PC y telefono esten en la misma red Wi-Fi.';
    }
    setState(() {
      _error = message;
    });
  }

  String _usernameFromEmail(String email) {
    final base = email
        .split('@')
        .first
        .replaceAll(RegExp(r'[^a-zA-Z0-9_]'), '');
    final safe = base.isEmpty ? 'usuario' : base;
    return '$safe${DateTime.now().millisecondsSinceEpoch % 100000}';
  }
}

/// Encabezado del bloque de mapa: muestra la lat/lng elegida y un botón
/// "Usar mi ubicación". Si todavía no hay pin, el botón aparece igual y la
/// línea de coordenadas se muestra en tono "sin seleccionar".
class _LocationLabel extends StatelessWidget {
  const _LocationLabel({
    required this.pin,
    required this.locating,
    required this.onUseMyLocation,
  });

  final LatLng? pin;
  final bool locating;
  final VoidCallback onUseMyLocation;

  @override
  Widget build(BuildContext context) {
    final pinned = pin;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Icon(Icons.place_outlined, color: Color(0xFF8B5E34)),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            pinned == null
                ? 'Ubicación sin seleccionar.'
                : '${pinned.latitude.toStringAsFixed(6)}, ${pinned.longitude.toStringAsFixed(6)}',
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 12,
              color: pinned == null
                  ? const Color(0xFFA08A78)
                  : const Color(0xFF4D3A2C),
              fontStyle: pinned == null ? FontStyle.italic : FontStyle.normal,
            ),
          ),
        ),
        TextButton.icon(
          onPressed: locating ? null : onUseMyLocation,
          icon: locating
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.my_location, size: 18),
          label: Text(locating ? 'Obteniendo...' : 'Mi ubicación'),
          style: TextButton.styleFrom(foregroundColor: const Color(0xFF8B5E34)),
        ),
      ],
    );
  }
}

class _HomeShell extends StatelessWidget {
  const _HomeShell({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFFFFF9EF),
      child: SafeArea(child: child),
    );
  }
}

class _LightScreen extends StatelessWidget {
  const _LightScreen({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 28),
        child: child,
      ),
    );
  }
}

class _StitchLogo extends StatelessWidget {
  const _StitchLogo();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.shield_outlined, color: Color(0xFF322214), size: 18),
            SizedBox(width: 6),
            Text(
              'RutaSOS',
              style: TextStyle(
                color: Color(0xFF322214),
                fontWeight: FontWeight.w700,
                fontSize: 20,
              ),
            ),
          ],
        ),
        SizedBox(height: 4),
        Text(
          'ASISTENCIA VEHICULAR INTELIGENTE',
          style: TextStyle(
            color: Color(0xFF4E453E),
            fontWeight: FontWeight.w700,
            fontSize: 12,
            letterSpacing: 0.6,
          ),
        ),
      ],
    );
  }
}

class _HeroButton extends StatelessWidget {
  const _HeroButton({
    required this.label,
    required this.onPressed,
    this.filled = false,
  });

  final String label;
  final VoidCallback onPressed;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 44,
      child: filled
          ? FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF322214),
                foregroundColor: const Color(0xFFFFFFFF),
                shape: const StadiumBorder(),
                textStyle: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              onPressed: onPressed,
              child: Text(label),
            )
          : OutlinedButton(
              style: OutlinedButton.styleFrom(
                backgroundColor: Colors.transparent,
                foregroundColor: const Color(0xFF322214),
                side: const BorderSide(color: Color(0xFF322214), width: 1.5),
                shape: const StadiumBorder(),
                textStyle: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              onPressed: onPressed,
              child: Text(label),
            ),
    );
  }
}

class _FeatureChipsScroller extends StatelessWidget {
  const _FeatureChipsScroller();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: const Row(
        children: [
          _FeatureMiniCard(
            badge: '24',
            title: '24/7',
            subtitle: 'atención disponible',
          ),
          SizedBox(width: 12),
          _FeatureMiniCard(
            badge: 'GPS',
            title: 'GPS',
            subtitle: 'seguimiento en vivo',
          ),
          SizedBox(width: 12),
          _FeatureMiniCard(
            badge: 'IA',
            title: 'IA',
            subtitle: 'apoyo para diagnóstico',
          ),
          SizedBox(width: 12),
          _FeatureMiniCard(
            badge: 'Bs',
            title: 'Planes',
            subtitle: 'para cada taller',
          ),
        ],
      ),
    );
  }
}

class _FeatureMiniCard extends StatelessWidget {
  const _FeatureMiniCard({
    required this.badge,
    required this.title,
    required this.subtitle,
  });

  final String badge;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      height: 72,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFD2C4BB).withValues(alpha: 0.2),
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A322214),
            blurRadius: 20,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: const Color(0xFFF9F3EA),
            child: Text(
              badge,
              style: const TextStyle(
                color: Color(0xFF322214),
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                    height: 1,
                  ),
                ),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 8,
                    color: Color(0xFF4E453E),
                    height: 1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StitchDivider extends StatelessWidget {
  const _StitchDivider();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 48,
          height: 1,
          color: const Color(0xFFD2C4BB).withValues(alpha: 0.45),
        ),
        const SizedBox(width: 14),
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
            color: const Color(0xFF715A3E).withValues(alpha: 0.35),
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 14),
        Container(
          width: 48,
          height: 1,
          color: const Color(0xFFD2C4BB).withValues(alpha: 0.45),
        ),
      ],
    );
  }
}

class _HomeStatsPanel extends StatelessWidget {
  const _HomeStatsPanel();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: const [
        _HomeStatusCard(
          color: Color(0xFF10B981),
          title: 'Red de talleres activa',
          subtitle: 'Mecánicos verificados en tu zona',
          badge: '+42 Online',
          badgeColor: Color(0xFF047857),
        ),
        SizedBox(height: 12),
        _HomeStatusCard(
          color: Color(0xFFF59E0B),
          title: 'Tiempo medio de respuesta',
          subtitle: 'Asistencia mecánica inmediata',
          badge: '~12 min',
          badgeColor: Color(0xFF92400E),
        ),
      ],
    );
  }
}

class _HomeStatusCard extends StatelessWidget {
  const _HomeStatusCard({
    required this.color,
    required this.title,
    required this.subtitle,
    required this.badge,
    required this.badgeColor,
  });

  final Color color;
  final String title;
  final String subtitle;
  final String badge;
  final Color badgeColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFD2C4BB).withValues(alpha: 0.18),
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A322214),
            blurRadius: 20,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFF322214),
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: Color(0xFF4E453E),
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              badge,
              style: TextStyle(
                color: badgeColor,
                fontWeight: FontWeight.w800,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SelectionCard extends StatelessWidget {
  const _SelectionCard({
    required this.badge,
    required this.title,
    required this.description,
    required this.action,
    required this.onTap,
  });

  final String badge;
  final String title;
  final String description;
  final String action;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 164,
      width: double.infinity,
      child: Card(
        color: Colors.white,
        elevation: 5,
        shadowColor: const Color(0xFFBFA58D).withValues(alpha: 0.16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundColor: const Color(0xFF2A1A10),
                  child: Text(
                    badge,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFF3D2B1F),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  description,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF6F655B),
                    fontSize: 12,
                    height: 1.25,
                  ),
                ),
                const Spacer(),
                Row(
                  children: [
                    Text(
                      action,
                      style: const TextStyle(
                        color: Color(0xFF3D2B1F),
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Icon(Icons.arrow_forward, size: 14),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Shell extends StatelessWidget {
  const _Shell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}

class _LoginUserStitchShell extends StatelessWidget {
  const _LoginUserStitchShell({
    super.key,
    required this.child,
    required this.onBack,
    required this.registerMode,
    required this.onToggleRegister,
  });

  final Widget child;
  final VoidCallback onBack;
  final bool registerMode;
  final VoidCallback onToggleRegister;

  @override
  Widget build(BuildContext context) {
    return _LoginGradientPage(
      child: Column(
        children: [
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
              child: Row(
                children: [
                  IconButton(
                    onPressed: onBack,
                    icon: const Icon(Icons.arrow_back),
                  ),
                  const SizedBox(width: 4),
                  const Text(
                    'RutaSOS',
                    style: TextStyle(
                      color: Color(0xFF322214),
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const Spacer(),
                  const Icon(
                    Icons.account_circle_outlined,
                    color: Color(0xFF322214),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
              children: [
                _LoginCard(
                  topIcon: Icons.lock,
                  title: registerMode ? 'Crear cuenta' : 'Login Usuarios',
                  subtitle: registerMode
                      ? 'Regístrate para pedir asistencia vial'
                      : 'Accede a tu cuenta de asistencia vial',
                  child: child,
                ),
                const SizedBox(height: 18),
                Center(
                  child: TextButton(
                    onPressed: onToggleRegister,
                    child: Text(
                      registerMode
                          ? '¿Ya tienes una cuenta? Login'
                          : '¿No tienes una cuenta? Regístrate',
                      style: const TextStyle(
                        color: Color(0xFF322214),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const _SecureFooter(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LoginAdminStitchShell extends StatelessWidget {
  const _LoginAdminStitchShell({
    super.key,
    required this.child,
    required this.onBack,
  });

  final Widget child;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return _LoginGradientPage(
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 32),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: IconButton(
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back),
              ),
            ),
            const SizedBox(height: 210),
            const Center(child: _AdminGlyph()),
            const SizedBox(height: 22),
            const Text(
              'Login Administrador',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF322214),
                fontSize: 24,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Accede al panel de control de RutaSOS para\ngestionar la red de seguridad.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFF4E453E), height: 1.4),
            ),
            const SizedBox(height: 28),
            _LoginCard(compact: true, child: child),
            const SizedBox(height: 34),
            const Center(
              child: Text("Don't have an admin account? Contact Support"),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoginWorkerStitchShell extends StatelessWidget {
  const _LoginWorkerStitchShell({
    super.key,
    required this.child,
    required this.onBack,
  });

  final Widget child;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return _LoginGradientPage(
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 28),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: IconButton.filledTonal(
                style: IconButton.styleFrom(
                  backgroundColor: const Color(0x33FFFFFF),
                ),
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back),
              ),
            ),
            const SizedBox(height: 42),
            Center(
              child: Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: const Color(0xFF322214),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x1A322214),
                      blurRadius: 18,
                      offset: Offset(0, 8),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 30),
            const Text(
              'Login Trabajadores',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF322214),
                fontSize: 29,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Accede para gestionar tus servicios y\ndisponibilidad',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF4E453E),
                fontSize: 16,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 42),
            _LoginCard(compact: true, child: child),
            const SizedBox(height: 28),
            const _SecureFooter(),
            const SizedBox(height: 18),
            const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Privacidad',
                  style: TextStyle(
                    color: Color(0xFFB6AAA0),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                SizedBox(width: 32),
                Text(
                  'Soporte',
                  style: TextStyle(
                    color: Color(0xFFB6AAA0),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _LoginGradientPage extends StatelessWidget {
  const _LoginGradientPage({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFF9EF), Color(0xFFDFD9D1)],
        ),
      ),
      child: child,
    );
  }
}

class _LoginCard extends StatelessWidget {
  const _LoginCard({
    required this.child,
    this.title,
    this.subtitle,
    this.topIcon,
    this.compact = false,
  });

  final Widget child;
  final String? title;
  final String? subtitle;
  final IconData? topIcon;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(24, compact ? 24 : 26, 24, 24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color(0x12715A3E),
            blurRadius: 20,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          if (topIcon != null) ...[
            CircleAvatar(
              radius: 24,
              backgroundColor: const Color(0xFF322214),
              child: Icon(topIcon, color: Colors.white),
            ),
            const SizedBox(height: 20),
          ],
          if (title != null) ...[
            Text(
              title!,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF322214),
                fontSize: 19,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
          ],
          if (subtitle != null) ...[
            Text(
              subtitle!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFF4E453E), height: 1.35),
            ),
            const SizedBox(height: 26),
          ],
          child,
        ],
      ),
    );
  }
}

Widget _stitchTextField(
  TextEditingController controller,
  String label, {
  String? hint,
  IconData? icon,
  IconData? suffixIcon,
  bool obscure = false,
  TextInputType? keyboard,
  ValueChanged<String>? onChanged,
}) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(
          color: Color(0xFF5C4A3D),
          fontWeight: FontWeight.w800,
          fontSize: 13,
          letterSpacing: 0.3,
        ),
      ),
      const SizedBox(height: 8),
      TextFormField(
        controller: controller,
        obscureText: obscure,
        keyboardType: keyboard,
        onChanged: onChanged,
        validator: (value) {
          final text = value?.trim() ?? '';
          if (text.isEmpty) return 'Este campo es obligatorio.';
          final lowerLabel = label.toLowerCase();
          if ((lowerLabel.contains('email') || lowerLabel.contains('correo')) &&
              !text.contains('@')) {
            return 'Ingresa un correo válido.';
          }
          if ((lowerLabel.contains('password') ||
                  lowerLabel.contains('contraseña')) &&
              text.length < 6) {
            return 'Mínimo 6 caracteres.';
          }
          return null;
        },
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: icon == null
              ? null
              : Icon(icon, color: const Color(0xFF80756D)),
          suffixIcon: suffixIcon == null
              ? null
              : Icon(suffixIcon, color: const Color(0xFF80756D)),
          filled: true,
          fillColor: const Color(0xFFFFF9EF),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 16,
          ),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFD2C4BB)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFF322214), width: 1.6),
          ),
        ),
      ),
    ],
  );
}

Widget _stitchLoginButton(String text, VoidCallback? onPressed) {
  return SizedBox(
    width: double.infinity,
    height: 54,
    child: FilledButton.icon(
      style: FilledButton.styleFrom(
        backgroundColor: const Color(0xFF322214),
        foregroundColor: Colors.white,
        disabledBackgroundColor: const Color(0xFFD2C4BB),
        shape: const StadiumBorder(),
        elevation: 8,
        shadowColor: const Color(0x40322214),
        textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
      ),
      onPressed: onPressed,
      label: Text(text),
      icon: const Icon(Icons.login),
      iconAlignment: IconAlignment.end,
    ),
  );
}

Widget _stitchError(String error) {
  return Padding(
    padding: const EdgeInsets.only(top: 14),
    child: Text(error, style: const TextStyle(color: Color(0xFFBA1A1A))),
  );
}

// ignore: unused_element
class _LoginDivider extends StatelessWidget {
  const _LoginDivider({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Expanded(child: Divider(color: Color(0xFFD2C4BB))),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF80756D),
              fontWeight: FontWeight.w800,
              fontSize: 12,
              letterSpacing: 1,
            ),
          ),
        ),
        const Expanded(child: Divider(color: Color(0xFFD2C4BB))),
      ],
    );
  }
}

// ignore: unused_element
class _SocialButton extends StatelessWidget {
  const _SocialButton({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        foregroundColor: const Color(0xFF322214),
        side: const BorderSide(color: Color(0xFFD2C4BB)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 15),
      ),
      onPressed: () {},
      child: Text(label),
    );
  }
}

class _AdminGlyph extends StatelessWidget {
  const _AdminGlyph();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 64,
      height: 64,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14715A3E),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.shield, size: 14, color: Color(0xFF322214)),
          SizedBox(width: 10),
          Icon(Icons.person, size: 14, color: Color(0xFF322214)),
        ],
      ),
    );
  }
}

class _SecureFooter extends StatelessWidget {
  const _SecureFooter();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Icon(Icons.verified_user_outlined, color: Color(0xFF9B8E83), size: 22),
        SizedBox(height: 24),
        Text(
          'VIAJA SEGURO CON\nRUTASOS',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Color(0xFF9B8E83),
            fontSize: 12,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.4,
          ),
        ),
      ],
    );
  }
}

class _FormShell extends StatelessWidget {
  const _FormShell({
    super.key,
    required this.title,
    required this.overline,
    required this.subtitle,
    required this.child,
    required this.error,
    required this.onBack,
  });

  final String title;
  final String overline;
  final String subtitle;
  final Widget child;
  final String error;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return _Shell(
      child: Card(
        color: Colors.white,
        elevation: 8,
        shadowColor: const Color(0x1A715A3E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextButton.icon(
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFF715A3E),
                  padding: EdgeInsets.zero,
                ),
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back),
                label: const Text('Volver'),
              ),
              const SizedBox(height: 8),
              Text(
                overline.toUpperCase(),
                style: const TextStyle(
                  color: Color(0xFF9A6634),
                  fontWeight: FontWeight.w900,
                  letterSpacing: 2,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                title,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: const Color(0xFF322214),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                subtitle,
                style: const TextStyle(color: Color(0xFF6F655B), height: 1.5),
              ),
              const SizedBox(height: 18),
              child,
              if (error.isNotEmpty) ...[
                const SizedBox(height: 14),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF1F0),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFF1C7C5)),
                  ),
                  child: Text(
                    error,
                    style: const TextStyle(color: Color(0xFFB3261E)),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StitchPlanCard extends StatelessWidget {
  const _StitchPlanCard({
    required this.plan,
    required this.onTap,
    this.popular = false,
  });

  final SaaSPlan plan;
  final VoidCallback onTap;
  final bool popular;

  @override
  Widget build(BuildContext context) {
    final admins = plan.maxAdministradores == null
        ? 'Ilimitados'
        : '${plan.maxAdministradores}';
    final mechanics = plan.maxMecanicos == null
        ? 'Ilimitados'
        : '${plan.maxMecanicos}';
    final requests = plan.maxSolicitudesMes == null
        ? 'Ilimitadas'
        : '${plan.maxSolicitudesMes}';
    final benefits = plan.beneficios.take(5).toList();
    final buttonColor = popular
        ? const Color(0xFF322214)
        : const Color(0xFF715A3E);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: popular ? const Color(0x55715A3E) : const Color(0xFFE7E2D9),
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A322214),
            blurRadius: 20,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Stack(
        children: [
          if (popular)
            Positioned(
              top: -24,
              right: -24,
              child: Container(
                padding: const EdgeInsets.fromLTRB(14, 6, 14, 7),
                decoration: const BoxDecoration(
                  color: Color(0xFF715A3E),
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(12),
                    topRight: Radius.circular(18),
                  ),
                ),
                child: const Text(
                  'POPULAR',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
              ),
            ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                plan.nombre.toUpperCase(),
                style: const TextStyle(
                  color: Color(0xFF715A3E),
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 2.2,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                plan.priceLabel.replaceAll('/mes', ''),
                style: const TextStyle(
                  color: Color(0xFF322214),
                  fontSize: 22,
                  height: 1.05,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                plan.descripcion,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Color(0xFF4E453E),
                  fontSize: 12,
                  height: 1.25,
                ),
              ),
              const SizedBox(height: 12),
              _StitchPlanLimit(label: 'Admins', value: admins),
              const SizedBox(height: 8),
              _StitchPlanLimit(label: 'Mecánicos', value: mechanics),
              const SizedBox(height: 8),
              _StitchPlanLimit(label: 'Solicitudes/mes', value: requests),
              const SizedBox(height: 14),
              ...benefits.map(
                (benefit) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 6),
                        child: Icon(
                          Icons.circle,
                          size: 5,
                          color: Color(0xFF715A3E),
                        ),
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          benefit,
                          style: const TextStyle(
                            color: Color(0xFF4E453E),
                            fontSize: 12,
                            height: 1.18,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                height: 44,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: buttonColor,
                    foregroundColor: Colors.white,
                    shape: const StadiumBorder(),
                    textStyle: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  onPressed: onTap,
                  child: const Text('Elegir plan'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StitchPlanLimit extends StatelessWidget {
  const _StitchPlanLimit({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 38,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF9F3EA),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFD2C4BB)),
      ),
      child: Row(
        children: [
          Text(
            label,
            style: const TextStyle(color: Color(0xFF4E453E), fontSize: 12),
          ),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF322214),
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.plan,
    required this.selected,
    required this.onTap,
  });

  final SaaSPlan plan;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final admins = plan.maxAdministradores == null
        ? 'Ilimitados'
        : '${plan.maxAdministradores}';
    final mechanics = plan.maxMecanicos == null
        ? 'Ilimitados'
        : '${plan.maxMecanicos}';
    final requests = plan.maxSolicitudesMes == null
        ? 'Ilimitadas'
        : '${plan.maxSolicitudesMes}';
    final benefits = plan.beneficios.isEmpty
        ? <String>[
            'Dashboard básico',
            'Tracking en tiempo real',
            'Soporte para taller',
          ]
        : plan.beneficios.take(5).toList();

    return Card(
      color: Colors.white,
      elevation: 6,
      shadowColor: const Color(0xFFC8AB90).withValues(alpha: 0.18),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
          color: selected ? const Color(0xFF8D5524) : const Color(0xFFE8D7C5),
          width: selected ? 1.4 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              plan.priceLabel.toUpperCase(),
              style: const TextStyle(
                color: Color(0xFF8D5524),
                fontSize: 10,
                letterSpacing: 1.6,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              plan.nombre,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 6),
            Text(
              plan.descripcion.trim().isEmpty
                  ? 'Plan inicial para validar un taller pequeño.'
                  : plan.descripcion,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Color(0xFF7A6556), fontSize: 12),
            ),
            const SizedBox(height: 14),
            _PlanLimitRow(label: 'Admins', value: admins),
            const SizedBox(height: 6),
            _PlanLimitRow(label: 'Mecánicos', value: mechanics),
            const SizedBox(height: 6),
            _PlanLimitRow(label: 'Solicitudes/mes', value: requests),
            const SizedBox(height: 12),
            ...benefits.map((benefit) => _PlanBullet(text: benefit)),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF735038),
                  foregroundColor: Colors.white,
                  shape: const StadiumBorder(),
                ),
                onPressed: onTap,
                child: const Text('Elegir plan'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlanLimitRow extends StatelessWidget {
  const _PlanLimitRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 32,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFCF8F3),
        border: Border.all(color: const Color(0xFFE8D7C5)),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Row(
        children: [
          Text(
            label,
            style: const TextStyle(color: Color(0xFF7A6556), fontSize: 11),
          ),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _PlanBullet extends StatelessWidget {
  const _PlanBullet({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Icon(Icons.circle, size: 4, color: Color(0xFF735038)),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 11, color: Color(0xFF5C4A3D)),
            ),
          ),
        ],
      ),
    );
  }
}
