"""
Modelos ORM (SQLAlchemy 2.x) para as tabelas analíticas do e-Fisco.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FatoEmpenho(Base):
    """
    Registros de Despesa Empenhada por Unidade Gestora.
    A unicidade garante que reexecuções diárias atualizem, não dupliquem.
    """

    __tablename__ = "fato_empenho"
    __table_args__ = (
        UniqueConstraint(
            "data_coleta",
            "unidade_gestora",
            "acao",
            "subacao",
            "data_empenho",
            "credor",
            name="uq_empenho_chave_negocio",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_coleta: Mapped[date] = mapped_column(Date, nullable=False)
    unidade_gestora: Mapped[str] = mapped_column(String(20), nullable=False)
    acao: Mapped[str] = mapped_column(String(20), nullable=False)
    subacao: Mapped[str] = mapped_column(String(20), nullable=False)
    data_empenho: Mapped[date | None] = mapped_column(Date, nullable=True)
    credor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valor_empenhado_item: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_empenhado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_liquidado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_pago: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<FatoEmpenho ug={self.unidade_gestora} acao={self.acao} "
            f"sub={self.subacao} data={self.data_empenho}>"
        )


class FatoFichaFinanceira(Base):
    """
    Registros da Ficha Financeira Detalhada do e-Fisco.
    """

    __tablename__ = "fato_ficha_financeira"
    __table_args__ = (
        UniqueConstraint(
            "data_coleta",
            "ficha_id",
            "exercicio",
            name="uq_ficha_chave_negocio",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_coleta: Mapped[date] = mapped_column(Date, nullable=False)
    ficha_id: Mapped[str] = mapped_column(String(50), nullable=False)
    exercicio: Mapped[str] = mapped_column(String(10), nullable=False)
    unidade_gestora: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gestao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grupo_despesa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fonte_recurso: Mapped[str | None] = mapped_column(String(200), nullable=True)
    natureza_despesa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dea: Mapped[str | None] = mapped_column(String(200), nullable=True)
    detalhamento_despesa: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    destinacao_recurso: Mapped[str | None] = mapped_column(String(200), nullable=True)
    situacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dotacao_inicial: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    dotacao_atual: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_empenhado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_liquidado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    valor_pago: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    saldo: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FatoFichaFinanceira ficha={self.ficha_id} exercicio={self.exercicio}>"
