import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Conferencia(Base):
    __tablename__ = "conferencias"
    __table_args__ = (UniqueConstraint("chave", "rodada"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(44))
    nota_id: Mapped[int | None] = mapped_column(ForeignKey("notas_fiscais.id"))
    rodada: Mapped[int] = mapped_column(default=1)
    operador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    filial_id: Mapped[int] = mapped_column(ForeignKey("filiais.id"))
    status: Mapped[str] = mapped_column(String(20), default="EM_ANDAMENTO")
    iniciada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Evento(Base):
    """Trilha de auditoria: só inserção. Nunca atualizar nem apagar."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    evento_uuid: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    conferencia_id: Mapped[int] = mapped_column(ForeignKey("conferencias.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    dados: Mapped[dict] = mapped_column(JSONB, default=dict)
    origem: Mapped[str] = mapped_column(String(10))  # leitor | camera | manual | sistema
    ts_dispositivo: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ts_servidor: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    dispositivo: Mapped[str] = mapped_column(String(100))
    filial_id: Mapped[int] = mapped_column(ForeignKey("filiais.id"))
