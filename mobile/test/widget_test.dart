import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:asistencia_mecanica_mobile/main.dart';

void main() {
  testWidgets('renderiza la app mobile', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const AsistenciaMecanicaApp());
    await tester.pumpAndSettle();

    expect(find.text('Acceso mobile'), findsOneWidget);
  });
}
