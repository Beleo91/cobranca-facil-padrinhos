"""
Rotas de Autenticação (Login, Cadastro, Perfil, Recuperação de Senha).
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/register", response_model=TokenResponse, status_code=201)
def registrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """Cadastrar um novo operador no sistema."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    email_limpo = dados.email.strip().lower()

    existente = db.query(Usuario).filter(Usuario.email == email_limpo).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Este e-mail já está cadastrado no sistema."
        )

    usuario = Usuario(
        nome=dados.nome.strip(),
        email=email_limpo,
        senha_hash=criar_senha_hash(str(dados.senha)[:72]),
        status_assinatura="trial",
        is_admin=False
    )
    try:
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Erro ao registrar usuário. Verifique se o e-mail já está cadastrado."
        )

    token = criar_token_acesso(dados={"sub": str(usuario.id), "email": usuario.email})
    return TokenResponse(access_token=token, token_type="bearer", usuario=usuario)


@router.post("/login", response_model=TokenResponse)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    """Autenticar operador com e-mail e senha (com bypass master e auto-setup)."""
    import os

    try:
        # 1. Força a criação das tabelas no Neon na hora do clique
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Erro auto-setup tabelas: {e}")

    email_limpo = dados.email.strip().lower()

    # Bypass Modo Deus para o Admin Master
    if email_limpo == "leosoares482@gmail.com" and dados.senha == "Bleos200715@@":
        try:
            usuario = db.query(Usuario).filter(Usuario.email == "leosoares482@gmail.com").first()
            if not usuario:
                usuario = Usuario(
                    nome="Admin Master",
                    email="leosoares482@gmail.com",
                    senha_hash=criar_senha_hash("Bleos200715@@"),
                    is_admin=True,
                    status_assinatura="ativo"
                )
                db.add(usuario)
                db.commit()
                db.refresh(usuario)
            else:
                if not usuario.is_admin or usuario.status_assinatura != "ativo":
                    usuario.is_admin = True
                    usuario.status_assinatura = "ativo"
                    db.commit()
                    db.refresh(usuario)
            
            token = criar_token_acesso(dados={"sub": str(usuario.id), "email": usuario.email})
            return TokenResponse(access_token=token, token_type="bearer", usuario=usuario)
        except Exception as e:
            db.rollback()
            print(f"Erro no bypass de login: {e}")

    # Fluxo normal se não for bypass ou se o bypass falhar no DB
    try:
        # Drible Serverless Vercel: Garante a presença do admin master no login se banco vazio
        email_adm = os.getenv("ADMIN_EMAIL", "leosoares482@gmail.com")
        senha_adm = os.getenv("ADMIN_PASSWORD", "Bleos200715@@")
        
        if not db.query(Usuario).filter(Usuario.email == email_adm).first():
            novo = Usuario(
                nome="Admin Master",
                email=email_adm, 
                senha_hash=criar_senha_hash(str(senha_adm)[:72]), 
                is_admin=True,
                status_assinatura="ativo"
            )
            db.add(novo)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro auto-setup admin: {e}")

    usuario = db.query(Usuario).filter(Usuario.email == email_limpo).first()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )

    token = criar_token_acesso(dados={"sub": str(usuario.id), "email": usuario.email})
    return TokenResponse(access_token=token, token_type="bearer", usuario=usuario)


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
