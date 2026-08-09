"""
Rotas Administrativas (Controle de Usuários e Assinaturas).
Apenas acessíveis por usuários com is_admin=True.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Usuario, Cliente, Emprestimo
from app.schemas import AdminUsuarioResumo, AlterarStatusRequest
from app.services.auth_service import obter_admin_atual

router = APIRouter(prefix="/admin", tags=["Administrador"])


@router.get("/usuarios", response_model=List[AdminUsuarioResumo])
def listar_todos_usuarios(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(obter_admin_atual)
):
    """Listar todos os usuários do sistema com contagem de clientes e empréstimos."""
    usuarios = db.query(Usuario).order_by(Usuario.criado_em.desc()).all()

    resultado = []
    for u in usuarios:
        total_clientes = db.query(Cliente).filter(Cliente.user_id == u.id).count()
        total_emprestimos = db.query(Emprestimo).filter(Emprestimo.user_id == u.id).count()

        resultado.append(AdminUsuarioResumo(
            id=u.id,
            nome=u.nome,
            email=u.email,
            status_assinatura=u.status_assinatura,
            is_admin=u.is_admin,
            total_clientes=total_clientes,
            total_emprestimos=total_emprestimos,
            criado_em=u.criado_em
        ))

    return resultado


@router.patch("/usuarios/{usuario_id}/status", response_model=AdminUsuarioResumo)
def alterar_status_usuario(
    usuario_id: int,
    dados: AlterarStatusRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(obter_admin_atual)
):
    """Alterar o status de assinatura de um usuário (trial, ativo, bloqueado)."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    usuario.status_assinatura = dados.status_assinatura
    db.commit()
    db.refresh(usuario)

    total_clientes = db.query(Cliente).filter(Cliente.user_id == usuario.id).count()
    total_emprestimos = db.query(Emprestimo).filter(Emprestimo.user_id == usuario.id).count()

    return AdminUsuarioResumo(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        status_assinatura=usuario.status_assinatura,
        is_admin=usuario.is_admin,
        total_clientes=total_clientes,
        total_emprestimos=total_emprestimos,
        criado_em=usuario.criado_em
    )
