import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../app_controller.dart';
import '../services/offline_queue_service.dart';

/// Banner discreto que muestra estado de conectividad + pendientes en cola.
/// Verde-marrón translucido cuando online + 0 pendientes (no se muestra).
/// Naranja cuando hay pendientes. Rojo cuando offline.
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _attach());
  }

  Future<void> _attach() async {
    if (!mounted) return;
    final ctrl = context.read<AppController>();
    _online = ctrl.connectivity.currentOnline;
    _pending = await ctrl.offlineQueue.pendingCount();
    if (!mounted) return;
    setState(() {});
    _connSub = ctrl.connectivity.isOnline$.listen((v) async {
      if (!mounted) return;
      final pendings = await ctrl.offlineQueue.pendingCount();
      setState(() {
        _online = v;
        _pending = pendings;
      });
    });
    _flushSub = ctrl.offlineQueue.events$.listen((r) async {
      if (!mounted) return;
      setState(() => _pending = r.pending);
      if (r.synced > 0) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
          SnackBar(content: Text('Sincronizadas ${r.synced} emergencia(s).')),
        );
      }
    });
  }

  @override
  void dispose() {
    _connSub?.cancel();
    _flushSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_online && _pending == 0) return const SizedBox.shrink();
    final color = !_online
        ? Colors.red.shade700
        : Colors.orange.shade700;
    final icon = !_online ? Icons.cloud_off : Icons.sync;
    final text = !_online
        ? (_pending > 0
            ? 'Sin conexión. $_pending emergencia(s) pendiente(s) de sincronización.'
            : 'Sin conexión. Las emergencias se guardarán localmente.')
        : '$_pending pendiente(s) de sincronización…';
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
