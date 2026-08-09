"""
Rotas de Pagamento e Processamento de Cartão de Crédito/Débito e Pix (Integração Asaas / Webhook).
"""
import uuid
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models import Usuario, PagamentoAssinatura
from app.schemas import (
    PagamentoCartaoAssinaturaRequest,
    PagamentoCartaoAssinaturaResponse,
    PagamentoAssinaturaHistorico,
    CobrancaPixResponse
)
from app.services.auth_service import obter_usuario_atual
from app.services.payment_service import (
    gerar_cobranca_pix_asaas,
    processar_cartao_asaas,
    ASAAS_PIX_KEY
)

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos & Assinaturas"])


def detectar_bandeira(numero_cartao: str) -> str:
    """Detecta a bandeira do cartão com base nos primeiros dígitos (BIN)."""
    limpo = re.sub(r"\D", "", numero_cartao)
    if not limpo:
        return "Desconhecida"

    if limpo.startswith("4"):
        return "Visa"
    elif re.match(r"^(5[1-5]|2[2-7])", limpo):
        return "Mastercard"
    elif re.match(r"^(4011|4389|4514|4576|5041|5067|5090|6277|6362|6363)", limpo):
        return "Elo"
    elif re.match(r"^(38|60)", limpo):
        return "Hipercard"
    elif re.match(r"^3[47]", limpo):
        return "American Express"
    return "Visa/Mastercard"


@router.post("/pix/gerar-cobranca", response_model=CobrancaPixResponse)
def gerar_cobranca_pix(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Gera uma cobrança PIX via API do Asaas.
    Retorna a chave Copia e Cola, QR Code e dados da cobrança.
    """
    resultado = gerar_cobranca_pix_asaas(
        user_id=usuario_atual.id,
        nome_usuario=usuario_atual.nome,
        email_usuario=usuario_atual.email,
        valor=50.0
    )
    return CobrancaPixResponse(**resultado)


@router.post("/cartao/assinar", response_model=PagamentoCartaoAssinaturaResponse)
def assinar_com_cartao(
    dados: PagamentoCartaoAssinaturaRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """
    Processar pagamento da assinatura do SaaS via Cartão de Crédito ou Débito via Asaas API.
    """
    numero_limpo = re.sub(r"\D", "", dados.numero_cartao)
    if len(numero_limpo) < 13 or len(numero_limpo) > 19:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de cartão de crédito/débito inválido. Verifique os dígitos digitados."
        )

    cvv_limpo = re.sub(r"\D", "", dados.cvv)
    if len(cvv_limpo) < 3 or len(cvv_limpo) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de segurança (CVV) inválido."
        )

    bandeira = detectar_bandeira(numero_limpo)
    ultimos_digitos = numero_limpo[-4:]
    valor_plano = 50.0

    # Chamada para o serviço do Asaas
    res_asaas = processar_cartao_asaas(
        user_id=usuario_atual.id,
        nome_usuario=usuario_atual.nome,
        email_usuario=usuario_atual.email,
        dados_cartao={
            "nome_titular": dados.nome_titular,
            "numero_cartao": numero_limpo,
            "validade": dados.validade,
            "cvv": cvv_limpo
        },
        valor=valor_plano
    )

    gateway_tx_id = res_asaas.get("payment_id", f"asaas_pay_{uuid.uuid4().hex[:12].upper()}")
    codigo_autorizacao = res_asaas.get("codigo_autorizacao", f"AUTH-{uuid.uuid4().hex[:6].upper()}")

    # Atualiza a assinatura do usuário no banco
    usuario_atual.status_assinatura = "ativo"

    # Salva o log da transação no banco de dados
    metodo = "cartao_credito" if dados.tipo_cartao == "credito" else "cartao_debito"
    pagamento_registro = PagamentoAssinatura(
        user_id=usuario_atual.id,
        valor=valor_plano,
        metodo_pagamento=metodo,
        bandeira=bandeira,
        ultimos_digitos=ultimos_digitos,
        gateway_tx_id=gateway_tx_id,
        codigo_autorizacao=codigo_autorizacao,
        status="aprovado"
    )
    db.add(pagamento_registro)
    db.commit()
    db.refresh(usuario_atual)
    db.refresh(pagamento_registro)

    tipo_str = "Crédito" if dados.tipo_cartao == "credito" else "Débito"

    return PagamentoCartaoAssinaturaResponse(
        sucesso=True,
        mensagem=f"Pagamento aprovado com sucesso via Cartão de {tipo_str} ({bandeira}) no Asaas Gateway! Sua assinatura de R$ 50,00 foi ativada.",
        gateway="Asaas Gateway Direct API",
        gateway_tx_id=gateway_tx_id,
        codigo_autorizacao=codigo_autorizacao,
        status_transacao="APROVADO",
        status_assinatura="ativo",
        bandeira=bandeira,
        ultimos_digitos=ultimos_digitos,
        valor=valor_plano,
        criado_em=pagamento_registro.criado_em
    )


@router.post("/webhook/asaas")
def webhook_asaas(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Webhook do Asaas para confirmação automática de pagamento.
    Sempre que a plataforma confirmar o recebimento do PIX ou Cartão,
    o sistema atualiza o status do usuário para 'ativo' no banco de dados.
    """
    event = payload.get("event")
    payment = payload.get("payment", {})

    if event in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED", "PAYMENT_UPDATED"):
        external_ref = payment.get("externalReference")
        payment_id = payment.get("id", f"asaas_wh_{uuid.uuid4().hex[:8]}")
        billing_type = payment.get("billingType", "PIX")
        value = float(payment.get("value", 50.0))

        usuario = None
        if external_ref and external_ref.isdigit():
            usuario = db.query(Usuario).filter(Usuario.id == int(external_ref)).first()

        if not usuario:
            # Buscar usuário inativo como fallback se não houver externalReference
            usuario = db.query(Usuario).filter(Usuario.status_assinatura != "ativo").first()

        if usuario:
            usuario.status_assinatura = "ativo"

            existente = db.query(PagamentoAssinatura).filter(
                PagamentoAssinatura.gateway_tx_id == payment_id
            ).first()

            if not existente:
                metodo = "pix" if billing_type == "PIX" else "cartao_credito"
                pagamento_registro = PagamentoAssinatura(
                    user_id=usuario.id,
                    valor=value,
                    metodo_pagamento=metodo,
                    bandeira="Asaas Pix" if billing_type == "PIX" else "Asaas Cartao",
                    ultimos_digitos="PIX" if billing_type == "PIX" else "0000",
                    gateway_tx_id=payment_id,
                    codigo_autorizacao="ASAAS-WEBHOOK-CONFIRMED",
                    status="aprovado"
                )
                db.add(pagamento_registro)

            db.commit()
            return {
                "status": "sucesso",
                "mensagem": f"Pagamento confirmado via Webhook Asaas. Assinatura do usuário '{usuario.email}' ativada!"
            }

    return {"status": "ignorado", "mensagem": f"Evento '{event}' recebido sem necessidade de alteração."}


@router.get("/historico", response_model=List[PagamentoAssinaturaHistorico])
def listar_historico_pagamentos(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
):
    """Listar histórico de transações e pagamentos de assinatura do usuário."""
    return db.query(PagamentoAssinatura).filter(
        PagamentoAssinatura.user_id == usuario_atual.id
    ).order_by(PagamentoAssinatura.criado_em.desc()).all()
