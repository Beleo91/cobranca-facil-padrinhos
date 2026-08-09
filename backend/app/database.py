"""
Configuração do banco de dados (SQLite com arquivo persistente ou PostgreSQL via DATABASE_URL).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Garantindo que a pasta do banco existe no Render
DB_PATH = "/opt/render/project/src/data"
try:
    os.makedirs(DB_PATH, exist_ok=True)
except Exception:
    # Se não estiver no Render, usa fallback local
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "data")
    os.makedirs(DB_PATH, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    db_path = os.path.join(DB_PATH, "emprestimos.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    print(f"[DATABASE] Usando SQLite em: {db_path}")
else:
    print(f"[DATABASE] Usando banco externo (DATABASE_URL definida).")

# Render usa URL antiga 'postgres://', SQLAlchemy exige 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,   # Valida conexão antes de usar (evita erros após sleep do Render)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency para injetar sessão do banco nas rotas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

