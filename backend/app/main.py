"""
Gestão de Empréstimos - API Principal com Autenticação e Sistema de Assinaturas.
"""
import os
import sys

# Adiciona caminhos ao sys.path para garantir resolução dos módulos (app, backend, etc.)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

for p in (ROOT_DIR, BACKEND_DIR, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app.models import Usuario  # noqa: F401  — garante que os models são registrados no Base
from app.services.auth_service import criar_senha_hash
from app.routes import clientes, emprestimos, dashboard, auth, admin, pagamentos

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


# ---------------------------------------------------------------------------
# Handler global: garante que qualquer erro 500 retorne JSON válido
# (resolve o erro: "Unexpected token 'I', 'Internal S'... is not valid JSON")
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Erro não tratado em {request.method} {request.url.path}:")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor. Por favor, tente novamente.",
            "erro": str(exc),
        },
    )

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Bleos200715@@")


@app.on_event("startup")
def inicializar_sistema():
    """Cria tabelas no banco e sincroniza o admin master via ORM."""

    # 1. Cria tabelas se não existirem
    try:
        print("[STARTUP] Verificando/criando tabelas...")
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Tabelas OK.")
    except Exception as e:
        print(f"[STARTUP ERROR] Falha ao verificar/criar tabelas: {e}")
        traceback.print_exc()

    # 2. Sincroniza o admin master via ORM
    db: Session = SessionLocal()
    try:
        # Se o usuário antigo 'leosoares@gmail.com' existir no banco, remove para evitar duplicidades
        old_admin = db.query(Usuario).filter(Usuario.email == "leosoares@gmail.com").first()
        if old_admin:
            db.delete(old_admin)
            db.commit()
            print("[STARTUP] Antigo admin leosoares@gmail.com removido.")

        # Busca pelo admin atual leosoares482@gmail.com
        admin = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()
        if admin:
            admin.senha_hash = criar_senha_hash(ADMIN_PASSWORD)
            admin.is_admin = True
            admin.status_assinatura = "ativo"
            print(f"[STARTUP] Admin ({ADMIN_EMAIL}) — senha sincronizada com sucesso.")
        else:
            admin = Usuario(
                nome="Administrador",
                email=ADMIN_EMAIL,
                senha_hash=criar_senha_hash(ADMIN_PASSWORD),
                is_admin=True,
                status_assinatura="ativo"
            )
            db.add(admin)
            print(f"[STARTUP] Admin ({ADMIN_EMAIL}) criado com sucesso.")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[STARTUP ERROR] Falha ao sincronizar admin: {e}")
        traceback.print_exc()
    finally:
        db.close()


FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/api/health")
def health_check():
    """Verificar se a API está online."""
    return {"status": "ok", "message": "API Gestão de Empréstimos SaaS online!"}
