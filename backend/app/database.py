import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuração de PYTHONPATH para Serverless
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for p in (ROOT_DIR, BACKEND_DIR, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Remove channel_binding se existir (causa erro em alguns drivers)
    if "channel_binding=require" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("?channel_binding=require", "")
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10
        }
    )
else:
    # Fallback para desenvolvimento local em SQLite
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception:
        data_dir = "/tmp"
        os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "emprestimos.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para injetar sessão do banco nas rotas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
