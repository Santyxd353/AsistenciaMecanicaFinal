import os
import time

import bcrypt
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, Session, create_engine, select

from app.models.user import User, UserRole

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    max_retries = int(os.getenv("DB_INIT_MAX_RETRIES", "10"))
    retry_delay = int(os.getenv("DB_INIT_RETRY_DELAY_SECONDS", "3"))

    for attempt in range(1, max_retries + 1):
        try:
            SQLModel.metadata.create_all(engine)
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
