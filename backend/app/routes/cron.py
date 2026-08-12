"""
Rota de Cron Job para a Vercel executar automaticamente tarefas agendadas (ex: lembretes de cobrança).
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Parcela, Emprestimo, Cliente, Usuario
from app.services.email_service import enviar_email_lembrete_cobranca

router = APIRouter(prefix="/cron", tags=["Cron Jobs"])


@router.get("/lembretes")
def executar_lembretes_cobranca(db: Session = Depends(get_db)):
    """
    Cron Job acionado diariamente pela Vercel.
    Busca parcelas com vencimento amanhã e envia lembrete por e-mail para o cliente/operador.
    """
    hoje = datetime.utcnow().date()
    amanha = hoje + timedelta(days=1)

    # Buscar parcelas não pagas que vencem amanhã
    parcelas_amanha = (
        db.query(Parcela)
        .filter(
            Parcela.paga == False,
            func.date(Parcela.data_vencimento) == amanha
        )
        .all()
    )

    lembretes_enviados = 0

    for p in parcelas_amanha:
        emprestimo = db.query(Emprestimo).filter(Emprestimo.id == p.emprestimo_id).first()
        if not emprestimo:
            continue
        
        cliente = db.query(Cliente).filter(Cliente.id == emprestimo.cliente_id).first()
        usuario = db.query(Usuario).filter(Usuario.id == emprestimo.user_id).first()

        destinatario = None
        nome_cliente = "Cliente"

        if cliente:
            nome_cliente = cliente.nome
        if usuario and usuario.email:
            destinatario = usuario.email

        if destinatario:
            data_str = amanha.strftime("%d/%m/%Y")
            sucesso = enviar_email_lembrete_cobranca(
                destinatario=destinatario,
                nome_cliente=nome_cliente,
                valor=p.valor,
                data_vencimento=data_str,
                num_parcela=p.numero
            )
            if sucesso:
                lembretes_enviados += 1

    return {"status": "ok", "lembretes_enviados": lembretes_enviados}
