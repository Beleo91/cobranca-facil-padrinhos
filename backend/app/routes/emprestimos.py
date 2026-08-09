"""
Rotas de Empréstimos e Parcelas com Multi-Tenancy e Regra de Bloqueio.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import Emprestimo, Parcela, Cliente, Usuario
from app.schemas import (
    EmprestimoCreate, EmprestimoResponse, EmprestimoResumo,
    ParcelaResponse, PagamentoCreate, SimulacaoRequest, SimulacaoResponse
)
from app.services.calculo_service import (
    calcular_parcelas_price,
    calcular_parcelas_juros_final,
    simular_emprestimo
)
from app.services.auth_service import obter_usuario_atual

router = APIRouter(prefix="/emprestimos", tags=["Empréstimos"])


def verificar_permissao_usuario(usuario: Usuario):
    """Verifica se a assinatura do usuário não está bloqueada."""
    if usuario.status_assinatura == "bloqueado":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está bloqueada. Não é possível cadastrar novos empréstimos ou registrar pagamentos."
        )


@router.post("/", response_model=EmprestimoResponse, status_code=201)
def criar_emprestimo(
    dados: EmprestimoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Criar um novo empréstimo e gerar automaticamente as parcelas (carnê)."""
    verificar_permissao_usuario(usuario_atual)

    # Validar se o cliente pertence a este usuário
    cliente = db.query(Cliente).filter(
        Cliente.id == dados.cliente_id,
        Cliente.user_id == usuario_atual.id
    ).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na sua carteira.")

    data_inicio = dados.data_inicio or datetime.utcnow()
    modalidade = dados.modalidade or "price"

    if modalidade == "juros_final":
        calculo = calcular_parcelas_juros_final(
            valor_principal=dados.valor_principal,
            taxa_juros_mensal=dados.taxa_juros,
            num_parcelas=dados.num_parcelas,
            data_inicio=data_inicio
        )
    else:
        calculo = calcular_parcelas_price(
            valor_principal=dados.valor_principal,
            taxa_juros_mensal=dados.taxa_juros,
            num_parcelas=dados.num_parcelas,
            data_inicio=data_inicio
        )

    emprestimo = Emprestimo(
        user_id=usuario_atual.id,
        cliente_id=dados.cliente_id,
        valor_principal=dados.valor_principal,
        taxa_juros=dados.taxa_juros,
        num_parcelas=dados.num_parcelas,
        valor_parcela=calculo["valor_parcela"],
        valor_total=calculo["valor_total"],
        data_inicio=data_inicio,
        descricao=dados.descricao,
        modalidade=modalidade,
        status="ativo"
    )
    db.add(emprestimo)
    db.flush()

    for p in calculo["parcelas"]:
        parcela = Parcela(
            emprestimo_id=emprestimo.id,
            numero=p["numero"],
            valor=p["valor"],
            juros=p.get("juros", 0.0),
            amortizacao=p.get("amortizacao", 0.0),
            data_vencimento=p["data_vencimento"],
            paga=False
        )
        db.add(parcela)

    db.commit()
    db.refresh(emprestimo)
    return emprestimo


@router.get("/", response_model=List[EmprestimoResumo])
def listar_emprestimos(
    cliente_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Listar empréstimos do usuário autenticado."""
    query = db.query(Emprestimo).filter(Emprestimo.user_id == usuario_atual.id)
    if cliente_id:
        query = query.filter(Emprestimo.cliente_id == cliente_id)
    if status:
        query = query.filter(Emprestimo.status == status)

    return query.order_by(Emprestimo.criado_em.desc()).offset(skip).limit(limit).all()


@router.get("/{emprestimo_id}", response_model=EmprestimoResponse)
def obter_emprestimo(
    emprestimo_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Obter detalhes completos de um empréstimo do usuário autenticado."""
    emprestimo = db.query(Emprestimo).filter(
        Emprestimo.id == emprestimo_id,
        Emprestimo.user_id == usuario_atual.id
    ).first()

    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")
    return emprestimo


@router.post("/{emprestimo_id}/parcelas/{parcela_id}/pagar", response_model=ParcelaResponse)
def pagar_parcela(
    emprestimo_id: int,
    parcela_id: int,
    pagamento: PagamentoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Registrar pagamento de uma parcela de empréstimo do usuário autenticado."""
    verificar_permissao_usuario(usuario_atual)

    emprestimo = db.query(Emprestimo).filter(
        Emprestimo.id == emprestimo_id,
        Emprestimo.user_id == usuario_atual.id
    ).first()

    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")

    parcela = db.query(Parcela).filter(
        Parcela.id == parcela_id,
        Parcela.emprestimo_id == emprestimo_id
    ).first()

    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada.")
    if parcela.paga:
        raise HTTPException(status_code=400, detail="Parcela já foi paga.")

    parcela.paga = True
    parcela.data_pagamento = datetime.utcnow()
    parcela.valor_pago = pagamento.valor_pago if pagamento.valor_pago is not None else parcela.valor
    parcela.metodo_pagamento = pagamento.metodo_pagamento or "pix"
    if pagamento.observacao:
        parcela.observacao = pagamento.observacao

    parcelas_pendentes = db.query(Parcela).filter(
        Parcela.emprestimo_id == emprestimo_id,
        Parcela.paga == False
    ).count()

    if parcelas_pendentes == 0:
        emprestimo.status = "quitado"

    db.commit()
    db.refresh(parcela)
    return parcela


@router.post("/simular", response_model=SimulacaoResponse)
def simular(dados: SimulacaoRequest):
    """Simular um empréstimo sem criar registros (aberto para todos)."""
    return simular_emprestimo(
        valor=dados.valor,
        taxa_juros=dados.taxa_juros,
        num_parcelas=dados.num_parcelas,
        modalidade=dados.modalidade or "price"
    )
