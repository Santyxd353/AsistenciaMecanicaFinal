import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _fullNameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isLogin = true;
  String _registerRole = 'client';
  String _error = '';

  @override
  void dispose() {
    _fullNameController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AppController>();

    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF1B1713), Color(0xFF5C2F16), Color(0xFFF6EBDC)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _isLogin ? 'Acceso mobile' : 'Crear cuenta',
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Cliente y taller comparten la misma cuenta del sistema.',
                          style: TextStyle(
                            color: Color(0xFF6F655B),
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 18),
                        SegmentedButton<bool>(
                          segments: const [
                            ButtonSegment<bool>(
                              value: true,
                              label: Text('Iniciar sesion'),
                            ),
                            ButtonSegment<bool>(
                              value: false,
                              label: Text('Registrarse'),
                            ),
                          ],
                          selected: {_isLogin},
                          onSelectionChanged: (value) {
                            setState(() {
                              _isLogin = value.first;
                              _error = '';
                            });
                          },
                        ),
                        if (!_isLogin) ...[
                          const SizedBox(height: 12),
                          SegmentedButton<String>(
                            segments: const [
                              ButtonSegment<String>(
                                value: 'client',
                                label: Text('Cliente'),
                              ),
                              ButtonSegment<String>(
                                value: 'workshop',
                                label: Text('Taller'),
                              ),
                            ],
                            selected: {_registerRole},
                            onSelectionChanged: (value) {
                              setState(() {
                                _registerRole = value.first;
                                _error = '';
                              });
                            },
                          ),
                        ],
                        const SizedBox(height: 18),
                        Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              if (!_isLogin) ...[
                                TextFormField(
                                  controller: _fullNameController,
                                  decoration: InputDecoration(
                                    labelText: _registerRole == 'client'
                                        ? 'Nombre completo'
                                        : 'Nombre del taller',
                                  ),
                                  validator: (value) {
                                    if (!_isLogin &&
                                        (value == null ||
                                            value.trim().isEmpty)) {
                                      return 'Este campo es obligatorio.';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 12),
                              ],
                              TextFormField(
                                controller: _usernameController,
                                decoration: const InputDecoration(
                                  labelText: 'Usuario',
                                ),
                                validator: (value) {
                                  if (value == null || value.trim().isEmpty) {
                                    return 'Ingresa un usuario.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              if (!_isLogin) ...[
                                TextFormField(
                                  controller: _emailController,
                                  decoration: const InputDecoration(
                                    labelText: 'Correo',
                                  ),
                                  validator: (value) {
                                    if (!_isLogin &&
                                        (value == null ||
                                            !value.contains('@'))) {
                                      return 'Ingresa un correo valido.';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 12),
                              ],
                              TextFormField(
                                controller: _passwordController,
                                decoration: const InputDecoration(
                                  labelText: 'Contrasena',
                                ),
                                obscureText: true,
                                validator: (value) {
                                  if (value == null || value.length < 6) {
                                    return 'Minimo 6 caracteres.';
                                  }
                                  return null;
                                },
                              ),
                            ],
                          ),
                        ),
                        if (_error.isNotEmpty) ...[
                          const SizedBox(height: 14),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFF1F0),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: const Color(0xFFF1C7C5),
                              ),
                            ),
                            child: Text(
                              _error,
                              style: const TextStyle(color: Color(0xFFB3261E)),
                            ),
                          ),
                        ],
                        const SizedBox(height: 18),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: controller.loading ? null : _submit,
                            child: Text(
                              controller.loading
                                  ? 'Procesando...'
                                  : (_isLogin
                                        ? 'Entrar'
                                        : (_registerRole == 'client'
                                              ? 'Crear cliente'
                                              : 'Crear taller')),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final controller = context.read<AppController>();
    setState(() => _error = '');

    try {
      if (_isLogin) {
        await controller.login(
          username: _usernameController.text.trim(),
          password: _passwordController.text,
        );
      } else if (_registerRole == 'client') {
        await controller.registerClient(
          username: _usernameController.text.trim(),
          email: _emailController.text.trim(),
          fullName: _fullNameController.text.trim(),
          password: _passwordController.text,
        );
      } else {
        await controller.registerWorkshop(
          username: _usernameController.text.trim(),
          email: _emailController.text.trim(),
          fullName: _fullNameController.text.trim(),
          password: _passwordController.text,
        );
      }
    } catch (error) {
      setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
      });
    }
  }
}
