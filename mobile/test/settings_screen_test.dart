import 'package:asistencia_mecanica_mobile/src/app_controller.dart';
import 'package:asistencia_mecanica_mobile/src/models.dart';
import 'package:asistencia_mecanica_mobile/src/screens/settings_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

class _FakeController extends AppController {
  var _loading = false;
  final List<Vehicle> _vehicles = [];

  @override
  bool get initialized => true;

  @override
  bool get loading => _loading;

  @override
  AppUser? get currentUser => const AppUser(
        id: 1,
        username: 'cliente',
        email: 'cliente@test.local',
        fullName: 'Cliente Test',
        role: 'driver',
        isActive: true,
      );

  @override
  String get baseUrl => 'http://10.0.2.2:8000';

  @override
  List<Vehicle> get vehicles => List.unmodifiable(_vehicles);

  @override
  Future<void> addVehicle({
    required String placa,
    required String marca,
    required String modelo,
    int? anio,
    required String color,
    String? photoPath,
  }) async {
    _loading = true;
    notifyListeners();
    _vehicles.add(
      Vehicle(
        localId: 'local-1',
        remoteId: 10,
        placa: placa.toUpperCase(),
        marca: marca,
        modelo: modelo,
        anio: anio,
        color: color,
        photoPath: photoPath,
      ),
    );
    _loading = false;
    notifyListeners();
  }
}

void main() {
  testWidgets('registra un vehiculo desde configuracion sin assert de Provider', (tester) async {
    final controller = _FakeController();
    await tester.binding.setSurfaceSize(const Size(430, 900));

    await tester.pumpWidget(
      ChangeNotifierProvider<AppController>.value(
        value: controller,
        child: const MaterialApp(home: SettingsScreen()),
      ),
    );

    await tester.drag(find.byType(ListView), const Offset(0, -420));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Registrar'));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextFormField, 'Placa'), 'abc123');
    await tester.enterText(find.widgetWithText(TextFormField, 'Marca'), 'Toyota');
    await tester.enterText(find.widgetWithText(TextFormField, 'Modelo'), 'Corolla');
    await tester.enterText(find.widgetWithText(TextFormField, 'Color'), 'Blanco');

    await tester.tap(find.widgetWithText(FilledButton, 'Guardar'));
    await tester.pumpAndSettle();

    expect(find.text('ABC123'), findsOneWidget);
    expect(find.textContaining('Toyota Corolla'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
