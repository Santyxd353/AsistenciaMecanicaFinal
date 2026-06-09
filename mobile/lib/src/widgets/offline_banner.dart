import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../services/offline_queue_service.dart';

/// Banner simple para mostrar conexion y emergencias offline pendientes.
class OfflineBanner extends StatefulWidget {
  const OfflineBanner({super.key});

  @override
  State<OfflineBanner> createState() => _OfflineBannerState();
}

class _OfflineBannerState extends State<OfflineBanner> {
  StreamSubscription<bool>? _connSub;
  StreamSubscription<OfflineFlushResult>? _flushSub;
  bool _online = true;
  int _pending = 0;
  int _failed = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _attach());
  }

  Future<void> _attach() async {
    if (!mounted) return;
    final ctrl = context.read<AppController>();
    _online = ctrl.connectivity.currentOnline;
    await _refreshCounts(ctrl);
    if (!mounted) return;
    setState(() {});

    _connSub = ctrl.connectivity.isOnline$.listen((online) async {
      if (!mounted) return;
      await _refreshCounts(ctrl);
      setState(() => _online = online);
    });

    _flushSub = ctrl.offlineQueue.events$.listen((result) async {
      if (!mounted) return;
      await _refreshCounts(ctrl);
      if (!mounted) return;
      setState(() {});
      if (result.synced > 0) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
          SnackBar(
            content: Text('Sincronizadas ${result.synced} emergencia(s).'),
          ),
        );
      }
    });
  }

  Future<void> _refreshCounts(AppController ctrl) async {
    final items = await ctrl.offlineQueue.visibleEmergencies();
    _pending = items.where((item) => item.isPending || item.isSyncing).length;
    _failed = items.where((item) => item.isError).length;
  }

  @override
  void dispose() {
    _connSub?.cancel();
    _flushSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_online && _pending == 0 && _failed == 0) {
      return const SizedBox.shrink();
    }

    final color = _failed > 0
        ? Colors.red.shade700
        : !_online
        ? Colors.red.shade700
        : Colors.orange.shade700;
    final icon = _failed > 0
        ? Icons.error_outline
        : !_online
        ? Icons.cloud_off
        : Icons.sync;
    final text = _failed > 0
        ? '$_failed emergencia(s) con error. Reintenta desde Inicio.'
        : !_online
        ? (_pending > 0
              ? 'Sin conexion. $_pending emergencia(s) pendiente(s) de sincronizacion.'
              : 'Sin conexion. Las emergencias se guardaran localmente.')
        : '$_pending pendiente(s) de sincronizacion...';

    return Material(
      color: color,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Row(
            children: [
              Icon(icon, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  text,
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
