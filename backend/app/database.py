"""
Configuração do banco de dados (SQLite adaptativo Vercel/Render/Local).
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Adiciona caminhos ao sys.path para garantir resolução de módulos em Serverless
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for p in (ROOT_DIR, BACKEND_DIR, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))

if IS_VERCEL:
    DB_PATH = "/tmp/emprestimos.db"
else:
    if os.path.isdir("/opt/render/project/src"):
        DATA_DIR = "/opt/render/project/src/data"
    else:
        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        DATA_DIR = "/tmp"
        os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, "emprestimos.db")

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DB_PATH}"

# Fix para PostgreSQL (postgres:// vs postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Inicializa as tabelas e garante o usuário administrador master."""
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from app.models import Usuario
            from app.services.auth_service import criar_senha_hash

            admin_email = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
            admin_password = os.getenv("ADMIN_PASSWORD", "Bleos200715@@")

            # Remove legado se existir
            old_admin = db.query(Usuario).filter(Usuario.email == "leosoares@gmail.com").first()
            if old_admin:
                db.delete(old_admin)
                db.commit()

            admin = db.query(Usuario).filter(Usuario.email == admin_email).first()
            if admin:
                admin.senha_hash = criar_senha_hash(admin_password)
                admin.is_admin = True
                admin.status_assinatura = "ativo"
            else:
                admin = Usuario(
                    nome="Administrador",
                    email=admin_email,
                    senha_hash=criar_senha_hash(admin_password),
                    is_admin=True,
                    status_assinatura="ativo"
                )
                db.add(admin)
            db.commit()
        except Exception as err:
            db.rollback()
            print(f"[INIT DB SESSION ERROR] {err}")
        finally:
            db.close()
    except Exception as e:
        print(f"[INIT DB ERROR] {e}")


# Se for Vercel, inicializa o banco imediatamente no cold start
if IS_VERCEL:
    init_db()

_db_initialized = False

def get_db():
    """Dependency para injetar sessão do banco nas rotas."""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


