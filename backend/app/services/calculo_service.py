"""
Serviço de Cálculo Financeiro.

Implementa a lógica de cálculo de parcelas e juros usando:
  - Sistema PRICE (parcelas fixas)
  - Juros Simples
  - Apenas Juros Mensais com Capital no Final (Bullet / Interest-Only)
"""
from datetime import datetime
from typing import List, Dict
from dateutil.relativedelta import relativedelta


def calcular_parcelas_price(valor_principal: float, taxa_juros_mensal: float, num_parcelas: int, data_inicio: datetime = None) -> Dict:
    """
    Calcula as parcelas usando a Tabela PRICE (parcelas fixas).
    """
    if data_inicio is None:
        data_inicio = datetime.utcnow()

    taxa = taxa_juros_mensal / 100.0

    if taxa > 0:
        fator = (taxa * (1 + taxa) ** num_parcelas) / ((1 + taxa) ** num_parcelas - 1)
        valor_parcela = round(valor_principal * fator, 2)
    else:
        valor_parcela = round(valor_principal / num_parcelas, 2)

    valor_total = round(valor_parcela * num_parcelas, 2)
    total_juros = round(valor_total - valor_principal, 2)

    parcelas = []
    saldo_devedor = valor_principal

    for i in range(1, num_parcelas + 1):
        data_vencimento = data_inicio + relativedelta(months=i)
        juros_parcela = round(saldo_devedor * taxa, 2)
        amortizacao = round(valor_parcela - juros_parcela, 2)
        saldo_devedor = max(0.0, round(saldo_devedor - amortizacao, 2))

        parcelas.append({
            "numero": i,
            "valor": valor_parcela,
            "data_vencimento": data_vencimento,
            "juros": juros_parcela,
            "amortizacao": amortizacao,
            "saldo_devedor": saldo_devedor
        })

    return {
        "valor_parcela": valor_parcela,
        "valor_total": valor_total,
        "total_juros": total_juros,
        "parcelas": parcelas
    }


def calcular_parcelas_juros_final(valor_principal: float, taxa_juros_mensal: float, num_parcelas: int, data_inicio: datetime = None) -> Dict:
    """
    Calcula as parcelas usando o modelo Bullet / Apenas Juros Mensais com Capital no Final.

    - Parcelas 1 a N-1: o devedor paga apenas os juros mensais (valor_principal × taxa)
    - Parcela N (última): paga os juros do mês + a devolução integral do capital principal

    Exemplo: R$ 1.000 em 6 meses a 5% a.m.
      Parcelas 1-5: R$ 50,00 (só juros)
      Parcela 6: R$ 1.050,00 (juros + principal)
    """
    if data_inicio is None:
        data_inicio = datetime.utcnow()

    taxa = taxa_juros_mensal / 100.0
    juros_mensais = round(valor_principal * taxa, 2)
    total_juros = round(juros_mensais * num_parcelas, 2)
    valor_total = round(valor_principal + total_juros, 2)

    parcelas = []

    for i in range(1, num_parcelas + 1):
        data_vencimento = data_inicio + relativedelta(months=i)
        eh_ultima = (i == num_parcelas)

        if eh_ultima:
            # Última parcela: juros + devolução do principal
            valor_parcela = round(juros_mensais + valor_principal, 2)
            amortizacao = valor_principal
        else:
            # Parcelas intermediárias: só os juros
            valor_parcela = juros_mensais
            amortizacao = 0.0

        # Saldo devedor: permanece = principal até último mês
        saldo_restante = 0.0 if eh_ultima else valor_principal

        parcelas.append({
            "numero": i,
            "valor": valor_parcela,
            "data_vencimento": data_vencimento,
            "juros": juros_mensais,
            "amortizacao": amortizacao,
            "saldo_devedor": saldo_restante
        })

    return {
        "valor_parcela": juros_mensais,       # valor das parcelas mensais de juros
        "valor_total": valor_total,
        "total_juros": total_juros,
        "parcelas": parcelas
    }


def calcular_parcelas_simples(valor_principal: float, taxa_juros_mensal: float, num_parcelas: int, data_inicio: datetime = None) -> Dict:
    """
    Calcula as parcelas usando Juros Simples.
    O valor total é: Principal + (Principal * taxa * N meses)
    Dividido igualmente entre as parcelas.
    """
    if data_inicio is None:
        data_inicio = datetime.utcnow()

    taxa = taxa_juros_mensal / 100.0
    total_juros = round(valor_principal * taxa * num_parcelas, 2)
    valor_total = round(valor_principal + total_juros, 2)
    valor_parcela = round(valor_total / num_parcelas, 2)

    parcelas = []
    for i in range(1, num_parcelas + 1):
        data_vencimento = data_inicio + relativedelta(months=i)
        parcelas.append({
            "numero": i,
            "valor": valor_parcela,
            "data_vencimento": data_vencimento,
            "juros": round(valor_principal * taxa, 2),
            "amortizacao": round(valor_principal / num_parcelas, 2),
            "saldo_devedor": 0.0
        })

    return {
        "valor_parcela": valor_parcela,
        "valor_total": valor_total,
        "total_juros": total_juros,
        "parcelas": parcelas
    }


def simular_emprestimo(valor: float, taxa_juros: float, num_parcelas: int, modalidade: str = "price") -> Dict:
    """
    Simula um empréstimo sem criar registros no banco.
    Retorna os valores calculados para exibição.
    """
    if modalidade == "juros_final":
        resultado = calcular_parcelas_juros_final(
            valor_principal=valor,
            taxa_juros_mensal=taxa_juros,
            num_parcelas=num_parcelas,
            data_inicio=datetime.utcnow()
        )
    else:
        resultado = calcular_parcelas_price(
            valor_principal=valor,
            taxa_juros_mensal=taxa_juros,
            num_parcelas=num_parcelas,
            data_inicio=datetime.utcnow()
        )

    return {
        "valor_principal": valor,
        "taxa_juros": taxa_juros,
        "num_parcelas": num_parcelas,
        "modalidade": modalidade,
        "valor_parcela": resultado["valor_parcela"],
        "valor_total": resultado["valor_total"],
        "total_juros": resultado["total_juros"]
    }
