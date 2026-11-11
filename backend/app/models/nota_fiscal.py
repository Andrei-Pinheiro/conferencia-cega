from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(44), unique=True)
    numero: Mapped[str] = mapped_column(String(9))
    serie: Mapped[str] = mapped_column(String(3))
    emitente_cnpj: Mapped[str] = mapped_column(String(14))
    emitente_nome: Mapped[str] = mapped_column(String(200))
    destinatario_cnpj: Mapped[str] = mapped_column(String(14))
    destinatario_nome: Mapped[str] = mapped_column(String(200))
    emissao: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    xml_original: Mapped[str] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(10))  # oracle | upload
    importada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    itens: Mapped[list["ItemNota"]] = relationship(
        back_populates="nota",
        cascade="all, delete-orphan",
        order_by="ItemNota.numero_item",
    )


class ItemNota(Base):
    __tablename__ = "itens_nota"
    __table_args__ = (UniqueConstraint("nota_id", "numero_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nota_id: Mapped[int] = mapped_column(ForeignKey("notas_fiscais.id"))
    numero_item: Mapped[int]
    codigo: Mapped[str] = mapped_column(String(60))
    ean: Mapped[str | None] = mapped_column(String(14))
    descricao: Mapped[str] = mapped_column(String(255))
    unidade_comercial: Mapped[str] = mapped_column(String(6))
    quantidade_comercial: Mapped[Decimal] = mapped_column(Numeric(15, 4))
    ean_tributavel: Mapped[str | None] = mapped_column(String(14))
    unidade_tributavel: Mapped[str] = mapped_column(String(6))
    quantidade_tributavel: Mapped[Decimal] = mapped_column(Numeric(15, 4))

    nota: Mapped["NotaFiscal"] = relationship(back_populates="itens")
    lotes: Mapped[list["LoteItem"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class LoteItem(Base):
    __tablename__ = "lotes_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("itens_nota.id"))
    lote: Mapped[str] = mapped_column(String(50))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(15, 4))
    fabricacao: Mapped[date | None] = mapped_column(Date)
    validade: Mapped[date | None] = mapped_column(Date)

    item: Mapped["ItemNota"] = relationship(back_populates="lotes")
