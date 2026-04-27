import os
import time

import bcrypt
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine, select

from app.models.user import User, UserRole
from app.services.storage import ensure_upload_root

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)


def ensure_legacy_schema():
    statements = [
        "ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS foto_url VARCHAR(500)",
        "ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS anio INTEGER",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS tiempo_estimado_minutos INTEGER",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'pendiente'",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS fecha_pago TIMESTAMP NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS especialidad_requerida_ia VARCHAR(120)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def init_db():
    max_retries = int(os.getenv("DB_INIT_MAX_RETRIES", "10"))
    retry_delay = int(os.getenv("DB_INIT_RETRY_DELAY_SECONDS", "3"))
    ensure_upload_root()

    for attempt in range(1, max_retries + 1):
        try:
            SQLModel.metadata.create_all(engine)
            ensure_legacy_schema()
            break
        except OperationalError:
            if attempt == max_retries:
                raise
            print(
                f"Base de datos no disponible. Reintento {attempt}/{max_retries} en {retry_delay}s..."
            )
            time.sleep(retry_delay)

    with Session(engine) as session:
        statement = select(User).where(User.username == "admin")
        admin = session.exec(statement).first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@sistemamecanico.com",
                full_name="Administrador",
                role=UserRole.ADMIN,
                is_active=True,
            )
            admin_user.hashed_password = bcrypt.hashpw(
                "admin123".encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            session.add(admin_user)
            session.commit()
            print("Usuario admin creado con exito!")


def get_session():
    with Session(engine) as session:
        yield session
