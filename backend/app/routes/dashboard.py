"""
Rota do Dashboard - Resumo geral do sistema filtrado por usuário.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Cliente, Emprestimo, Parcela, Usuario
from app.schemas import DashboardResponse
from app.services.auth_service import obter_usuario_atual

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardResponse)
def obter_dashboard(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Retorna o resumo geral das finanças para o usuário autenticado."""
    total_clientes = db.query(func.count(Cliente.id)).filter(
        Cliente.user_id == usuario_atual.id,
        Cliente.ativo == True
    ).scalar() or 0

    total_emprestimos_ativos = db.query(func.count(Emprestimo.id)).filter(
        Emprestimo.user_id == usuario_atual.id,
        Emprestimo.status == "ativo"
    ).scalar() or 0

    valor_total_emprestado = db.query(func.sum(Emprestimo.valor_principal)).filter(
        Emprestimo.user_id == usuario_atual.id,
        Emprestimo.status.in_(["ativo", "quitado"])
    ).scalar() or 0.0

    valor_total_a_receber = db.query(func.sum(Parcela.valor)).join(Emprestimo).filter(
        Emprestimo.user_id == usuario_atual.id,
        Parcela.paga == False
    ).scalar() or 0.0

    valor_total_recebido = db.query(func.sum(Parcela.valor_pago)).join(Emprestimo).filter(
        Emprestimo.user_id == usuario_atual.id,
        Parcela.paga == True
    ).scalar() or 0.0

    agora = datetime.utcnow()
    parcelas_vencidas = db.query(func.count(Parcela.id)).join(Emprestimo).filter(
        Emprestimo.user_id == usuario_atual.id,
        Parcela.paga == False,
        Parcela.data_vencimento < agora
    ).scalar() or 0

    em_7_dias = agora + timedelta(days=7)
    parcelas_a_vencer_7_dias = db.query(func.count(Parcela.id)).join(Emprestimo).filter(
        Emprestimo.user_id == usuario_atual.id,
        Parcela.paga == False,
        Parcela.data_vencimento >= agora,
        Parcela.data_vencimento <= em_7_dias
    ).scalar() or 0

    limite_trial_atingido = (
        usuario_atual.status_assinatura == "trial" and total_clientes >= 2
    )

    return DashboardResponse(
        total_clientes=total_clientes,
        total_emprestimos_ativos=total_emprestimos_ativos,
        valor_total_emprestado=valor_total_emprestado,
        valor_total_a_receber=valor_total_a_receber,
        valor_total_recebido=valor_total_recebido,
        parcelas_vencidas=parcelas_vencidas,
        parcelas_a_vencer_7_dias=parcelas_a_vencer_7_dias,
        status_assinatura=usuario_atual.status_assinatura,
        limite_trial_atingido=limite_trial_atingido
    )
