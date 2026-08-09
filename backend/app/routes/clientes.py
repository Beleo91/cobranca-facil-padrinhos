"""
Rotas de Clientes - CRUD completo com Multi-Tenancy, Trial e Contatos Expandidos.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Cliente, Usuario
from app.schemas import ClienteCreate, ClienteUpdate, ClienteResponse
from app.services.auth_service import obter_usuario_atual

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def verificar_permissao_usuario(usuario: Usuario):
    """Verifica se a assinatura do usuário não está bloqueada."""
    if usuario.status_assinatura == "bloqueado":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está bloqueada por pendência na assinatura. Assine o plano para continuar utilizando o sistema."
        )


@router.post("/", response_model=ClienteResponse, status_code=201)
def criar_cliente(
    cliente: ClienteCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Cadastrar um novo cliente para o usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    # Regra de Trial: Máximo 2 clientes cadastrados no plano trial
    total_clientes = db.query(Cliente).filter(Cliente.user_id == usuario_atual.id).count()
    if total_clientes >= 2 and usuario_atual.status_assinatura == "trial":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você atingiu o limite de teste. Assine o plano mensal de R$ 50 para continuar."
        )

    # Verificar CPF duplicado para este usuário
    existente = db.query(Cliente).filter(
        Cliente.user_id == usuario_atual.id,
        Cliente.cpf == cliente.cpf.strip()
    ).first()

    if existente:
        raise HTTPException(status_code=400, detail="Você já possui um cliente cadastrado com este CPF.")

    db_cliente = Cliente(
        user_id=usuario_atual.id,
        nome=cliente.nome.strip(),
        cpf=cliente.cpf.strip(),
        instagram=cliente.instagram.strip() if cliente.instagram else None,
        telefone=cliente.telefone.strip() if cliente.telefone else None,
        telefone_2=cliente.telefone_2.strip() if cliente.telefone_2 else None,
        telefone_3=cliente.telefone_3.strip() if cliente.telefone_3 else None,
        endereco=cliente.endereco.strip() if cliente.endereco else None,
        observacoes=cliente.observacoes.strip() if cliente.observacoes else None
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    busca: Optional[str] = Query(None, description="Buscar por nome, CPF ou Instagram"),
    ativo: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Listar clientes do usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    query = db.query(Cliente).filter(Cliente.user_id == usuario_atual.id)
    if busca:
        busca_str = f"%{busca}%"
        query = query.filter(
            (Cliente.nome.ilike(busca_str)) |
            (Cliente.cpf.ilike(busca_str)) |
            (Cliente.instagram.ilike(busca_str))
        )
    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)

    return query.order_by(Cliente.nome).offset(skip).limit(limit).all()


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Obter detalhes de um cliente do usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.user_id == usuario_atual.id
    ).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cliente_id: int,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Atualizar dados de um cliente do usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.user_id == usuario_atual.id
    ).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if isinstance(valor, str):
            valor = valor.strip() if valor.strip() else None
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def deletar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Remover um cliente do usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.user_id == usuario_atual.id
    ).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    db.delete(cliente)
    db.commit()
    return None
