import os
from sqlmodel import create_engine, Session, SQLModel, select, text
from dotenv import load_dotenv

from app.models.user import User, UserRole
from app.core.security import get_password_hash

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    # Solo crea las tablas si no existen — los datos persisten entre reinicios
    SQLModel.metadata.create_all(engine)
    
    # Crear usuario admin por defecto solo si no existe
    with Session(engine) as session:
        statement = select(User).where(User.username == "admin")
        admin = session.exec(statement).first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@sistemamecanico.com",
                full_name="Administrador",
                role=UserRole.ADMIN,
                is_active=True
            )
            import bcrypt
            admin_user.hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            session.add(admin_user)
            session.commit()
            print("Usuario admin creado con éxito!")

def get_session():
    with Session(engine) as session:
        yield session
