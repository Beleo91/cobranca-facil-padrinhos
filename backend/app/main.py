"""
Gestão de Empréstimos - API Principal com Autenticação e Sistema de Assinaturas.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.models import Usuario
from app.services.auth_service import criar_senha_hash
from app.routes import clientes, emprestimos, dashboard, auth, admin, pagamentos

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestão de Empréstimos API",
    description="API SaaS para controle de empréstimos, carnês, autenticação e assinaturas.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(clientes.router, prefix="/api")
app.include_router(emprestimos.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(pagamentos.router, prefix="/api")

ADMIN_EMAIL = "leosoares482@gmail.com"
ADMIN_PASSWORD = "Bleos200715@@"


@app.on_event("startup")
def criar_usuario_admin_inicial():
    """Garante que o administrador principal esteja cadastrado e ativo no sistema."""
    db: Session = SessionLocal()
    try:
        admin_existente = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()
        if not admin_existente:
            admin = Usuario(
                nome="Administrador",
                email=ADMIN_EMAIL,
                senha_hash=criar_senha_hash(ADMIN_PASSWORD),
                status_assinatura="ativo",
                is_admin=True
            )
            db.add(admin)
            db.commit()
            print(f"[STARTUP] Admin master ({ADMIN_EMAIL}) criado com sucesso!")
        else:
            admin_existente.is_admin = True
            admin_existente.status_assinatura = "ativo"
            db.commit()
            print(f"[STARTUP] Admin master ({ADMIN_EMAIL}) atualizado!")
    except Exception as e:
        print(f"[STARTUP ERROR] Erro ao verificar admin inicial: {e}")
    finally:
        db.close()


FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/api/health")
def health_check():
    """Verificar se a API está online."""
    return {"status": "ok", "message": "API Gestão de Empréstimos SaaS online!"}
