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

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
# Senha do administrador — atualizada diretamente no startup e sincronizada no banco a cada deploy
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "BleosDAO2026@@")


@app.on_event("startup")
def inicializar_sistema():
    """Cria tabelas no banco, migra colunas faltantes e sincroniza o admin master."""
    from sqlalchemy import text

    # 1. Cria tabelas novas (CREATE TABLE IF NOT EXISTS)
    try:
        print("[STARTUP] Criando/verificando tabelas no banco de dados...")
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Tabelas OK.")
    except Exception as e:
        print(f"[STARTUP ERROR] Falha ao criar tabelas: {e}")
        traceback.print_exc()
        return

    # 2. Migração manual de colunas — SQLite não suporta ALTER automaticamente pelo create_all
    # Cada comando é executado individualmente; erro = coluna já existe (ignorado).
    colunas_novas = [
        "ALTER TABLE usuarios ADD COLUMN reset_token VARCHAR(128)",
        "ALTER TABLE usuarios ADD COLUMN reset_token_expira DATETIME",
    ]
    with engine.connect() as conn:
        for sql in colunas_novas:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[STARTUP] Migração aplicada: {sql}")
            except Exception:
                pass  # Coluna já existe — normal

    # 3. Sincroniza senha e privilégios do admin via SQL puro
    #    (imune a colunas faltantes no ORM)
    senha_hash = criar_senha_hash(ADMIN_PASSWORD)
    with engine.connect() as conn:
        try:
            # Verifica se o admin existe
            resultado = conn.execute(
                text("SELECT id FROM usuarios WHERE email = :email"),
                {"email": ADMIN_EMAIL}
            ).fetchone()

            if resultado:
                conn.execute(
                    text("""
                        UPDATE usuarios
                        SET senha_hash = :hash,
                            is_admin   = 1,
                            status_assinatura = 'ativo'
                        WHERE email = :email
                    """),
                    {"hash": senha_hash, "email": ADMIN_EMAIL}
                )
                conn.commit()
                print(f"[STARTUP] Admin ({ADMIN_EMAIL}) — senha e privilégios sincronizados com sucesso.")
            else:
                # Cria o admin do zero
                conn.execute(
                    text("""
                        INSERT INTO usuarios (nome, email, senha_hash, status_assinatura, is_admin)
                        VALUES ('Administrador', :email, :hash, 'ativo', 1)
                    """),
                    {"email": ADMIN_EMAIL, "hash": senha_hash}
                )
                conn.commit()
                print(f"[STARTUP] Admin ({ADMIN_EMAIL}) criado com sucesso.")

        except Exception as e:
            print(f"[STARTUP ERROR] Falha ao sincronizar admin: {e}")
            traceback.print_exc()


FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/api/health")
def health_check():
    """Verificar se a API está online."""
    return {"status": "ok", "message": "API Gestão de Empréstimos SaaS online!"}
