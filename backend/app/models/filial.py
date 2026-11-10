from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.models.base import Base


class Filial(Base):
    __tablename__ = "filiais"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True)
    ativa: Mapped[bool] = mapped_column(default=True)
