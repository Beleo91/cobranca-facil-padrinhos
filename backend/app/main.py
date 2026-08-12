"""
Gestão de Empréstimos - API Principal
"""
import os
import sys
import traceback
from datetime import datetime

# ===== sys.path correto =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # backend/app
BACKEND_DIR = os.path.dirname(BASE_DIR)                        # backend
ROOT_DIR = os.path.dirname(BACKEND_DIR)                        # raiz do projeto

for p in (ROOT_DIR, BACKEND_DIR, BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal, get_db
from app.models import Usuario
from app.services.auth_service import criar_senha_hash, criar_token_acesso
from app.routes import auth, admin, clientes, emprestimos, dashboard, pagamentos, cron

app = FastAPI(
    title="Gestão de Empréstimos API",
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

# ===== Rotas =====
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(clientes.router, prefix="/api")
app.include_router(emprestimos.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(pagamentos.router, prefix="/api")
app.include_router(cron.router, prefix="/api")

# ===== Handler global de erro (sempre retorna JSON) =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor", "error": str(exc)}
    )

# ===== Health e Setup =====
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "API online"}

@app.get("/api/setup")
@app.get("/setup")
def setup_database(db: Session = Depends(get_db)):
    try:
        Base.metadata.create_all(bind=engine)
        email = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
        senha = os.getenv("ADMIN_PASSWORD", "Bleos200715@@")
        admin = db.query(Usuario).filter(Usuario.email == email).first()
        if not admin:
            admin = Usuario(
                nome="Admin Master",
                email=email,
                senha_hash=criar_senha_hash(senha),
                is_admin=True,
                status_assinatura="ativo"
            )
            db.add(admin)
            db.commit()
            return {"status": "sucesso", "mensagem": "Tabelas e Admin criados"}
        return {"status": "ok", "mensagem": "Já configurado"}
    except Exception as e:
        traceback.print_exc()
        return {"status": "erro", "mensagem": str(e)}

# ===== Startup: garante admin master =====
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        email = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
        senha = os.getenv("ADMIN_PASSWORD", "Bleos200715@@")
        admin = db.query(Usuario).filter(Usuario.email == email).first()
        if not admin:
            admin = Usuario(
                nome="Admin Master",
                email=email,
                senha_hash=criar_senha_hash(senha),
                is_admin=True,
                status_assinatura="ativo"
            )
            db.add(admin)
        else:
            admin.senha_hash = criar_senha_hash(senha)
            admin.is_admin = True
            admin.status_assinatura = "ativo"
        db.commit()
        db.close()
        print("[STARTUP] Admin master sincronizado")
    except Exception as e:
        print(f"[STARTUP ERROR] {e}")
        traceback.print_exc()
