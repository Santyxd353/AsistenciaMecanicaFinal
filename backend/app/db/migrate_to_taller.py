"""
Script de migración para implementar el modelo Taller.

Este script debe ejecutarse UNA SOLA VEZ después de actualizar los modelos
para migrar los datos existentes de usuarios WORKSHOP a la nueva tabla taller.
"""

import os
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select
from app.models.user import User, UserRole
from app.models.domain import Taller, Tecnico, Solicitud

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)


def migrate_to_taller_model():

    with Session(engine) as session:
        try:
            # 1. Encontrar todos los usuarios con role WORKSHOP
            workshop_users = session.exec(
                select(User).where(User.role == UserRole.WORKSHOP)
            ).all()

            print(f"📋 Encontrados {len(workshop_users)} usuarios WORKSHOP")

            talleres_creados = 0
            tecnicos_actualizados = 0
            solicitudes_actualizadas = 0

            for user in workshop_users:
                # 2. Crear un taller para cada usuario WORKSHOP
                taller = Taller(
                    nombre_comercial=f"Taller de {user.full_name or user.username}",
                    direccion="Dirección por definir",
                    telefono="Teléfono por definir",
                    email_contacto=user.email,
                    horario_atencion="Lunes-Domingo 8:00-18:00",
                    especialidades='["Mecánica General"]',
                    descripcion=f"Taller propiedad de {user.full_name or user.username}",
                    propietario_id=user.id,
                    # Valores por defecto para otros campos
                    calificacion_promedio=0.0,
                    total_servicios_completados=0,
                    notificaciones_nuevas_asignaciones=True,
                    notificaciones_push=True,
                    notificaciones_recordatorios=True,
                    notificaciones_pagos=True,
                    reportes_semanales=False
                )

                session.add(taller)
                session.flush()  # Para obtener el ID del taller
                talleres_creados += 1

                # 3. Actualizar técnicos que apuntaban a este usuario
                tecnicos = session.exec(
                    select(Tecnico).where(Tecnico.taller_id == user.id)
                ).all()

                for tecnico in tecnicos:
                    tecnico.taller_id = taller.id
                    session.add(tecnico)
                    tecnicos_actualizados += 1

                # 4. Actualizar solicitudes que apuntaban a este usuario
                solicitudes = session.exec(
                    select(Solicitud).where(Solicitud.taller_id == user.id)
                ).all()

                for solicitud in solicitudes:
                    solicitud.taller_id = taller.id
                    session.add(solicitud)
                    solicitudes_actualizadas += 1

            # 5. Commit de todos los cambios
            session.commit()

            print("🎉 Migración completada exitosamente!")
            print(f"   📊 Talleres creados: {talleres_creados}")
            print(f"   👷 Técnicos actualizados: {tecnicos_actualizados}")
            print(f"   📋 Solicitudes actualizadas: {solicitudes_actualizadas}")

        except Exception as e:
            session.rollback()
            print(f"❌ Error durante la migración: {e}")
            raise


if __name__ == "__main__":
    print("⚠️  ADVERTENCIA: Este script modificará la base de datos.")
    print("   Asegúrate de tener un backup antes de continuar.")
    confirm = input("¿Deseas continuar? (escribe 'SÍ' para confirmar): ")

    if confirm.upper() == "SÍ":
        migrate_to_taller_model()
    else:
        print("Migración cancelada.")