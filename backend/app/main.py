"""
Gestão de Empréstimos - API Principal com Autenticação e Sistema de Assinaturas.
"""
import os
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

ADMIN_EMAIL = "leosoares482@gmail.com"
ADMIN_PASSWORD = "Bleos200715@@"


@app.on_event("startup")
def inicializar_sistema():
    """Reset completo do banco de dados e recriação do admin master."""

    # 1. Reset e recriação de tabelas
    try:
        print("[STARTUP] Resetando e recriando tabelas...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Tabelas resetadas e recriadas com sucesso.")
    except Exception as e:
        print(f"[STARTUP ERROR] Falha ao resetar/recriar tabelas: {e}")
        traceback.print_exc()

    # 2. Sincroniza o admin master via ORM
    db: Session = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()
        if admin:
            admin.senha_hash = criar_senha_hash(ADMIN_PASSWORD[:72])
            admin.is_admin = True
            admin.status_assinatura = "ativo"
            db.commit()
            print(f"[STARTUP] Admin ({ADMIN_EMAIL}) — senha sincronizada com sucesso.")
        else:
            novo_admin = Usuario(
                nome="Administrador",
                email=ADMIN_EMAIL,
                senha_hash=criar_senha_hash(ADMIN_PASSWORD[:72]),
                status_assinatura="ativo",
                is_admin=True
            )
            db.add(novo_admin)
            db.commit()
            print(f"[STARTUP] Admin ({ADMIN_EMAIL}) criado com sucesso.")
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
