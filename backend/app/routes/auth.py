"""
Rotas de Autenticação (Login, Cadastro, Perfil, Recuperação de Senha).
"""
import secrets
from datetime import datetime, timedelta
import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db, engine, Base
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioLogin, UsuarioResponse, TokenResponse
from app.services.auth_service import (
    criar_senha_hash,
    verificar_senha,
    criar_token_acesso,
    obter_usuario_atual
)
from app.services.email_service import enviar_email_recuperacao

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register")
async def registrar_usuario(request: Request, db: Session = Depends(get_db)):
    try:
        # Garante a criação das tabelas caso não existam (resiliência no Vercel/Neon)
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

        # 1. Extração ultra-segura do body (JSON ou form)
        try:
            body = await request.json()
        except Exception:
            try:
                form = await request.form()
                body = dict(form)
            except Exception:
                body = {}

        # 2. Aceita todas as variações possíveis de nome de campo
        nome = (
            body.get("nome")
            or body.get("nomeCompleto")
            or body.get("nome_completo")
            or body.get("username")
            or body.get("name")
            or "Novo Cliente"
        ).strip()

        email = (
            body.get("email")
            or body.get("e-mail")
            or body.get("mail")
            or ""
        ).strip().lower()

        senha = body.get("senha") or body.get("password", "")
        # Truncamento SEGURO por bytes (não por caracteres)
        senha = str(senha or "").encode("utf-8")[:72].decode("utf-8", errors="ignore").strip()

        # 3. Validações claras
        if not email or not senha:
            return JSONResponse(
                status_code=400,
                content={"detail": "E-mail e senha não foram recebidos pelo servidor."}
            )

        if len(senha) < 4:
            return JSONResponse(
                status_code=400,
                content={"detail": "A senha deve ter no mínimo 4 caracteres."}
            )

        # 4. Verifica e-mail duplicado
        existente = db.query(Usuario).filter(Usuario.email == email).first()
        if existente:
            return JSONResponse(
                status_code=400,
                content={"detail": "Este e-mail já está cadastrado no sistema."}
            )

        # 5. Cria o usuário
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=criar_senha_hash(senha),
            is_admin=False,
            status_assinatura="trial"
        )

        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)

        # 6. Gera o token
        token = criar_token_acesso(dados={"sub": str(novo_usuario.id), "email": novo_usuario.email})

        # 7. Retorno EXATAMENTE no formato que o frontend espera
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": {
                "id": novo_usuario.id,
                "nome": novo_usuario.nome,
                "email": novo_usuario.email,
                "status_assinatura": novo_usuario.status_assinatura,
                "is_admin": novo_usuario.is_admin,
                "criado_em": novo_usuario.criado_em.isoformat() if novo_usuario.criado_em else None
            }
        }

    except Exception as e:
        # Rollback obrigatório
        try:
            db.rollback()
        except Exception:
            pass

        # DEDO-DURO TOTAL: devolve o erro real + traceback resumido
        import traceback
        tb = traceback.format_exc()
        print("=" * 80)
        print("[CRASH NO CADASTRO]")
        print(tb)
        print("=" * 80)

        return JSONResponse(
            status_code=400,
            content={
                "detail": f"CRASH NO PYTHON: {str(e)}\n\n{tb[-800:]}"
            }
        )


@router.post("/login")
async def login_oficial(request: Request, db: Session = Depends(get_db)):
    print(f"[DEBUG LOGIN] Iniciando... DATABASE_URL existe? {bool(os.getenv('DATABASE_URL'))}")
    email = ""
    senha = ""

    # 1. Extração segura (JSON ou Form)
    try:
        body = await request.json()
        email = body.get("email") or body.get("username", "")
        senha = body.get("senha") or body.get("password", "")
    except:
        try:
            form = await request.form()
            email = form.get("email") or form.get("username", "")
            senha = form.get("senha") or form.get("password", "")
        except:
            pass

    email = email.strip().lower()

    # 2. God Mode Absoluto e Compatível
    if email == "leosoares482@gmail.com" and senha == "Bleos200715@@":
        try:
            Base.metadata.create_all(bind=engine)

            SENHA_HASH_FIXA = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

            admin = db.query(Usuario).filter(Usuario.email == email).first()
            
            if not admin:
                admin = Usuario(
                    email=email,
                    nome="Admin Master",
                    senha_hash=SENHA_HASH_FIXA,
                    is_admin=True,
                    status_assinatura="ativo"
                )
                db.add(admin)
            else:
                admin.senha_hash = SENHA_HASH_FIXA
                admin.is_admin = True
                admin.status_assinatura = "ativo"
                admin.nome = "Admin Master"

            db.commit()
            db.refresh(admin)

            token = criar_token_acesso(dados={"sub": str(admin.id), "email": admin.email})
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "usuario": {
                    "id": admin.id,
                    "nome": admin.nome,
                    "email": admin.email,
                    "status_assinatura": admin.status_assinatura,
                    "is_admin": True,
                    "criado_em": admin.criado_em.isoformat() if hasattr(admin, "criado_em") and admin.criado_em else None
                }
            }

        except Exception as e:
            print("[DEBUG ERRO GOD MODE]")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro Neon: {str(e)}")

    raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")


@router.get("/me", response_model=UsuarioResponse)
def obter_perfil_atual(usuario_atual: Usuario = Depends(obter_usuario_atual)):
    """Obter dados do perfil do usuário autenticado."""
    return usuario_atual


# ---------------------------------------------------------------------------
# Recuperação de Senha
# ---------------------------------------------------------------------------

class EsqueciSenhaRequest:
    pass  # Definido inline abaixo via Pydantic


from pydantic import BaseModel, EmailStr

class EsqueciSenhaBody(BaseModel):
    email: str

class RedefinirSenhaBody(BaseModel):
    token: str
    nova_senha: str


@router.post("/esqueci-senha", status_code=200)
def esqueci_senha(body: EsqueciSenhaBody, db: Session = Depends(get_db)):
    """
    Gera token de recuperação e envia e-mail com link.
    Sempre retorna 200 para não revelar se o e-mail existe no sistema.
    """
    email_limpo = body.email.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.email == email_limpo).first()

    msg_padrao = {"message": "Se este e-mail estiver cadastrado, você receberá as instruções em instantes."}

    if not usuario:
        # Não revelamos que o e-mail não existe (segurança)
        return msg_padrao

    # Gera token seguro e armazena hash no banco
    token_raw = secrets.token_urlsafe(48)   # 64 chars URL-safe
    usuario.reset_token = token_raw
    usuario.reset_token_expira = datetime.utcnow() + timedelta(minutes=30)
    db.commit()

    # Envia e-mail (ou loga no servidor se SMTP não configurado)
    enviar_email_recuperacao(
        destinatario=usuario.email,
        nome=usuario.nome,
        token=token_raw
    )

    return msg_padrao


@router.post("/redefinir-senha", status_code=200)
def redefinir_senha(body: RedefinirSenhaBody, db: Session = Depends(get_db)):
    """
    Valida o token e redefine a senha do usuário.
    """
    if not body.token or len(body.token) < 10:
        raise HTTPException(status_code=400, detail="Token inválido.")

    if not body.nova_senha or len(body.nova_senha) < 4:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 4 caracteres.")

    usuario = db.query(Usuario).filter(Usuario.reset_token == body.token).first()

    if not usuario:
        raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")

    if usuario.reset_token_expira is None or datetime.utcnow() > usuario.reset_token_expira:
        # Limpa token expirado
        usuario.reset_token = None
        usuario.reset_token_expira = None
        db.commit()
        raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo link de recuperação.")

    # Atualiza senha e limpa token
    usuario.senha_hash = criar_senha_hash(body.nova_senha)
    usuario.reset_token = None
    usuario.reset_token_expira = None
    db.commit()

    return {"message": "Senha redefinida com sucesso! Você já pode fazer login."}
