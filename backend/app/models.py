"""
Modelos do banco de dados - SQLAlchemy ORM com Suporte a Multi-Tenancy, Usuários, Contatos Expandidos e Métodos de Pagamento (Cartão Crédito/Débito, Pix).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Usuario(Base):
    """Modelo de Usuário / Operador do Sistema."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    status_assinatura = Column(String(20), default="trial", nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    ultimo_acesso = Column(DateTime, default=datetime.utcnow)
    # Campos para recuperação de senha
    reset_token = Column(String(128), nullable=True, index=True)
    reset_token_expira = Column(DateTime, nullable=True)

    clientes = relationship("Cliente", back_populates="usuario", cascade="all, delete-orphan")
    emprestimos = relationship("Emprestimo", back_populates="usuario", cascade="all, delete-orphan")
    pagamentos_assinatura = relationship("PagamentoAssinatura", back_populates="usuario", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        senha = kwargs.pop("senha", None)
        if senha and "senha_hash" not in kwargs:
            from app.services.auth_service import criar_senha_hash
            kwargs["senha_hash"] = criar_senha_hash(senha)
        if "status_assinatura" not in kwargs:
            kwargs["status_assinatura"] = "trial"
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Usuario(id={self.id}, email='{self.email}', status='{self.status_assinatura}')>"


class Cliente(Base):
    """Modelo de Cliente (vinculado a um usuário, com múltiplos contatos)."""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nome = Column(String(200), nullable=False, index=True)
    cpf = Column(String(14), nullable=False)
    instagram = Column(String(100), nullable=True)
    telefone = Column(String(20), nullable=True)      # Principal
    telefone_2 = Column(String(20), nullable=True)    # Secundário / Parente 1
    telefone_3 = Column(String(20), nullable=True)    # Parente 2
    endereco = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="clientes")
    emprestimos = relationship("Emprestimo", back_populates="cliente", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cliente(id={self.id}, nome='{self.nome}', user_id={self.user_id})>"


class Emprestimo(Base):
    """Modelo de Empréstimo (Carnê, vinculado a um usuário e cliente)."""
    __tablename__ = "emprestimos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    valor_principal = Column(Float, nullable=False)
    taxa_juros = Column(Float, nullable=False)
    num_parcelas = Column(Integer, nullable=False)
    valor_parcela = Column(Float, nullable=False)
    valor_total = Column(Float, nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    descricao = Column(Text, nullable=True)
    status = Column(String(20), default="ativo")
    modalidade = Column(String(20), default="price", nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="emprestimos")
    cliente = relationship("Cliente", back_populates="emprestimos")
    parcelas = relationship("Parcela", back_populates="emprestimo", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Emprestimo(id={self.id}, valor={self.valor_principal}, user_id={self.user_id})>"


class Parcela(Base):
    """Modelo de Parcela individual do carnê."""
    __tablename__ = "parcelas"

    id = Column(Integer, primary_key=True, index=True)
    emprestimo_id = Column(Integer, ForeignKey("emprestimos.id"), nullable=False)
    numero = Column(Integer, nullable=False)
    valor = Column(Float, nullable=False)
    juros = Column(Float, default=0.0, nullable=True)
    amortizacao = Column(Float, default=0.0, nullable=True)
    data_vencimento = Column(DateTime, nullable=False)
    data_pagamento = Column(DateTime, nullable=True)
    paga = Column(Boolean, default=False)
    valor_pago = Column(Float, default=0.0)
    metodo_pagamento = Column(String(50), nullable=True)  # pix, dinheiro, cartao_credito, cartao_debito
    observacao = Column(Text, nullable=True)

    emprestimo = relationship("Emprestimo", back_populates="parcelas")

    def __repr__(self):
        return f"<Parcela(num={self.numero}, valor={self.valor}, paga={self.paga}, metodo={self.metodo_pagamento})>"


class PagamentoAssinatura(Base):
    """Registro de transação de pagamento de assinatura (Simulação Gateway Mercado Pago / Asaas)."""
    __tablename__ = "pagamentos_assinatura"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    valor = Column(Float, nullable=False)
    metodo_pagamento = Column(String(50), nullable=False)  # cartao_credito, cartao_debito, pix
    bandeira = Column(String(50), nullable=True)           # visa, mastercard, elo, etc.
    ultimos_digitos = Column(String(4), nullable=True)
    gateway_tx_id = Column(String(100), nullable=False)
    codigo_autorizacao = Column(String(50), nullable=False)
    status = Column(String(30), default="aprovado", nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="pagamentos_assinatura")

    def __repr__(self):
        return f"<PagamentoAssinatura(id={self.id}, user_id={self.user_id}, tx={self.gateway_tx_id}, status={self.status})>"
