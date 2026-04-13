import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models.dart';

class RequestDetailScreen extends StatelessWidget {
  const RequestDetailScreen({
    super.key,
    required this.request,
    required this.meta,
    required this.vehicleLabel,
  });

  final EmergencyRequest request;
  final LocalRequestMeta? meta;
  final String vehicleLabel;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('dd/MM/yyyy · HH:mm');

    return Scaffold(
      appBar: AppBar(title: Text('Solicitud #${request.id}')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
        children: [
          _SectionCard(
            title: 'Estado actual',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatusPill(status: request.estado, label: request.statusLabel),
                const SizedBox(height: 14),
                _InfoLine(label: 'Vehiculo', value: vehicleLabel),
                _InfoLine(label: 'Fecha', value: formatter.format(request.fechaCreacion.toLocal())),
                _InfoLine(
                  label: 'Ubicacion',
                  value: '${request.latitud.toStringAsFixed(6)}, ${request.longitud.toStringAsFixed(6)}',
                ),
                _InfoLine(
                  label: 'Tecnico asignado',
                  value: request.tecnicoId?.toString() ?? 'Aun no asignado',
                ),
                _InfoLine(
                  label: 'Taller',
                  value: request.tallerId?.toString() ?? 'Pendiente de asignacion',
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Analisis del backend',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoLine(label: 'Clasificacion IA', value: request.clasificacionIa ?? 'Sin clasificar'),
                _InfoLine(label: 'Prioridad', value: request.prioridadIa ?? 'Sin prioridad'),
                _InfoLine(label: 'Resumen', value: request.resumenIa ?? request.descripcion),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _SectionCard(
            title: 'Adjuntos y notas mobile',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoLine(label: 'Tipo reportado', value: meta?.issueType ?? 'No registrado'),
                _InfoLine(label: 'Fotos', value: '${meta?.imagePaths.length ?? 0} archivo(s)'),
                _InfoLine(
                  label: 'Audio',
                  value: meta?.audioPath == null ? 'Sin audio' : _fileName(meta!.audioPath!),
                ),
                _InfoLine(
                  label: 'Notas',
                  value: meta?.extraNotes.trim().isEmpty ?? true ? 'Sin notas adicionales' : meta!.extraNotes,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _fileName(String path) => path.split(RegExp(r'[\\/]')).last;
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF6F655B), fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, height: 1.4)),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status, required this.label});

  final String status;
  final String label;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'pendiente' => const Color(0xFF9C5C00),
      'asignada' => const Color(0xFF0F5CBD),
      'en_progreso' => const Color(0xFF6E46C2),
      'resuelta' => const Color(0xFF167B47),
      'cancelada' => const Color(0xFFA22C29),
      _ => const Color(0xFF5F554B),
    };

    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          label,
          style: TextStyle(color: color, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
