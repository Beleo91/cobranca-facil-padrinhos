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
from app.services.auth_service import obter_usuario_atual

router = APIRouter(prefix="/admin", tags=["Administrador"])


@router.get("/usuarios", response_model=List[AdminUsuarioResumo])
def listar_todos_usuarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Listar todos os usuários do sistema."""
    if not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado.")

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


@router.put("/usuarios/{usuario_id}/status", response_model=AdminUsuarioResumo)
def alterar_status_usuario(
    usuario_id: int,
    dados: AlterarStatusRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Alterar o status de assinatura de um usuário (trial, ativo, bloqueado)."""
    if not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    user_alvo = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user_alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user_alvo.status_assinatura = dados.status_assinatura
    db.commit()
    db.refresh(user_alvo)

    total_clientes = db.query(Cliente).filter(Cliente.user_id == user_alvo.id).count()
    total_emprestimos = db.query(Emprestimo).filter(Emprestimo.user_id == user_alvo.id).count()

    return AdminUsuarioResumo(
        id=user_alvo.id,
        nome=user_alvo.nome,
        email=user_alvo.email,
        status_assinatura=user_alvo.status_assinatura,
        is_admin=user_alvo.is_admin,
        total_clientes=total_clientes,
        total_emprestimos=total_emprestimos,
        criado_em=user_alvo.criado_em
    )


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Excluir um usuário e todos os seus dados vinculados do sistema."""
    if not usuario.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem excluir usuários.")

    user_alvo = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user_alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    db.delete(user_alvo)
    db.commit()

    return {"mensagem": f"Usuário #{usuario_id} e seus dados vinculados foram excluídos com sucesso."}
