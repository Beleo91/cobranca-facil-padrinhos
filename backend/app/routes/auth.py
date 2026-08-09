"""
Rotas de Autenticação (Login, Cadastro, Perfil).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioLogin, UsuarioResponse, TokenResponse
from app.services.auth_service import (
    criar_senha_hash,
    verificar_senha,
    criar_token_acesso,
    obter_usuario_atual
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def registrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """Cadastrar um novo operador no sistema."""
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
        senha_hash=criar_senha_hash(dados.senha),
        status_assinatura="trial",
        is_admin=False
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = criar_token_acesso(dados={"sub": str(usuario.id), "email": usuario.email})
    return TokenResponse(access_token=token, token_type="bearer", usuario=usuario)


@router.post("/login", response_model=TokenResponse)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    """Autenticar operador com e-mail e senha."""
    email_limpo = dados.email.strip().lower()
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
