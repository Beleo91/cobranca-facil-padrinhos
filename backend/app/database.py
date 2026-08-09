"""
Configuração do banco de dados (SQLite com arquivo persistente ou PostgreSQL via DATABASE_URL).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------
# Resolução do diretório de dados — prioriza disco persistente do Render
# -----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1) Variável explícita definida pelo usuário
# 2) Disco persistente padrão do Render (mountPath configurado no render.yaml)
# 3) Fallback local (desenvolvimento)
DATA_DIR = (
    os.getenv("SQLITE_DATA_DIR")
    or "/opt/render/project/src/data"
    if os.path.isdir("/opt/render/project/src")
    else os.path.join(os.path.dirname(BASE_DIR), "data")
)

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError as e:
    # Se não conseguir criar no path preferido, cai para diretório local
    print(f"[DATABASE] Aviso: não foi possível criar {DATA_DIR}: {e}. Usando diretório local.")
    DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
    os.makedirs(DATA_DIR, exist_ok=True)

print(f"[DATABASE] Diretório de dados: {DATA_DIR}")

# -----------------------------------------------------------------------
# URL de conexão — PostgreSQL (Supabase/Render Postgres) ou SQLite
# -----------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    db_path = os.path.join(DATA_DIR, "emprestimos.db")
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

