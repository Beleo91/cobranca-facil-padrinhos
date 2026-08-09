"""
Schemas Pydantic para validação de dados da API com suporte a contatos expandidos e pagamentos via cartão de crédito/débito.
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Usuários & Autenticação
# ---------------------------------------------------------------------------

class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., min_length=5, max_length=200)
    senha: str = Field(..., min_length=4)


class UsuarioLogin(BaseModel):
    email: str
    senha: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: str
    status_assinatura: str
    is_admin: bool
    criado_em: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class AdminUsuarioResumo(BaseModel):
    id: int
    nome: str
    email: str
    status_assinatura: str
    is_admin: bool
    total_clientes: int
    total_emprestimos: int
    criado_em: datetime

    class Config:
        from_attributes = True


class AlterarStatusRequest(BaseModel):
    status_assinatura: Literal["trial", "ativo", "bloqueado"]


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class ClienteBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    cpf: str = Field(..., min_length=11, max_length=14)
    instagram: Optional[str] = None
    telefone: Optional[str] = None      # Telefone Principal
    telefone_2: Optional[str] = None    # Secundário / Parente 1
    telefone_3: Optional[str] = None    # Parente 2
    endereco: Optional[str] = None
    observacoes: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    instagram: Optional[str] = None
    telefone: Optional[str] = None
    telefone_2: Optional[str] = None
    telefone_3: Optional[str] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    id: int
    user_id: int
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Empréstimo & Parcelas
# ---------------------------------------------------------------------------

class EmprestimoCreate(BaseModel):
    cliente_id: int
    valor_principal: float = Field(..., gt=0, description="Valor emprestado")
    taxa_juros: float = Field(..., ge=0, description="Taxa de juros mensal (%)")
    num_parcelas: int = Field(..., gt=0, le=360, description="Número de parcelas")
    data_inicio: Optional[datetime] = None
    descricao: Optional[str] = None
    modalidade: Optional[Literal["price", "juros_final"]] = Field(
        default="price",
        description="Modalidade de cálculo"
    )


class ParcelaResponse(BaseModel):
    id: int
    numero: int
    valor: float
    juros: Optional[float] = 0.0
    amortizacao: Optional[float] = 0.0
    data_vencimento: datetime
    data_pagamento: Optional[datetime] = None
    paga: bool
    valor_pago: Optional[float] = 0.0
    metodo_pagamento: Optional[str] = None
    observacao: Optional[str] = None

    class Config:
        from_attributes = True


class EmprestimoResponse(BaseModel):
    id: int
    user_id: int
    cliente_id: int
    valor_principal: float
    taxa_juros: float
    num_parcelas: int
    valor_parcela: float
    valor_total: float
    data_inicio: datetime
    descricao: Optional[str] = None
    status: str
    modalidade: str = "price"
    criado_em: datetime
    cliente: Optional[ClienteResponse] = None
    parcelas: List[ParcelaResponse] = []

    class Config:
        from_attributes = True


class EmprestimoResumo(BaseModel):
    id: int
    user_id: int
    cliente_id: int
    valor_principal: float
    taxa_juros: float
    num_parcelas: int
    valor_parcela: float
    valor_total: float
    data_inicio: datetime
    status: str
    modalidade: str = "price"
    criado_em: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Pagamento de Parcelas
# ---------------------------------------------------------------------------

class PagamentoCreate(BaseModel):
    valor_pago: Optional[float] = None
    metodo_pagamento: Optional[Literal["pix", "dinheiro", "cartao_credito", "cartao_debito"]] = Field(
        default="pix",
        description="Forma de pagamento utilizada pelo cliente"
    )
    observacao: Optional[str] = None


# ---------------------------------------------------------------------------
# Pagamento de Assinatura via Cartão (Mercado Pago / Asaas Mock)
# ---------------------------------------------------------------------------

class PagamentoCartaoAssinaturaRequest(BaseModel):
    tipo_cartao: Literal["credito", "debito"] = Field(default="credito")
    numero_cartao: str = Field(..., min_length=13, max_length=19, description="Número do cartão de crédito ou débito")
    nome_titular: str = Field(..., min_length=2, max_length=100, description="Nome impresso no cartão")
    validade: str = Field(..., min_length=4, max_length=7, description="Validade MM/AA")
    cvv: str = Field(..., min_length=3, max_length=4, description="Código de segurança CVV")
    salvar_cartao: Optional[bool] = False


class PagamentoCartaoAssinaturaResponse(BaseModel):
    sucesso: bool
    mensagem: str
    gateway: str = "Mercado Pago / Asaas"
    gateway_tx_id: str
    codigo_autorizacao: str
    status_transacao: str
    status_assinatura: str
    bandeira: str
    ultimos_digitos: str
    valor: float
    criado_em: datetime


class CobrancaPixResponse(BaseModel):
    sucesso: bool
    payment_id: str
    pix_copia_e_cola: str
    encoded_image: Optional[str] = ""
    expiration_date: Optional[str] = None
    valor: float
    chave_estatica: str


class PagamentoAssinaturaHistorico(BaseModel):
    id: int
    user_id: int
    valor: float
    metodo_pagamento: str
    bandeira: Optional[str] = None
    ultimos_digitos: Optional[str] = None
    gateway_tx_id: str
    codigo_autorizacao: str
    status: str
    criado_em: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Dashboard & Simulador
# ---------------------------------------------------------------------------

class DashboardResponse(BaseModel):
    total_clientes: int
    total_emprestimos_ativos: int
    valor_total_emprestado: float
    valor_total_a_receber: float
    valor_total_recebido: float
    parcelas_vencidas: int
    parcelas_a_vencer_7_dias: int
    status_assinatura: str
    limite_trial_atingido: bool


class SimulacaoRequest(BaseModel):
    valor: float = Field(..., gt=0)
    taxa_juros: float = Field(..., ge=0)
    num_parcelas: int = Field(..., gt=0, le=360)
    modalidade: Optional[Literal["price", "juros_final"]] = Field(
        default="price",
        description="Modalidade de cálculo"
    )


class SimulacaoResponse(BaseModel):
    valor_principal: float
    taxa_juros: float
    num_parcelas: int
    modalidade: str
    valor_parcela: float
    valor_total: float
    total_juros: float
