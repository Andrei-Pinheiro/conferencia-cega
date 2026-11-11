import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import usuario_atual
from app.core.chave import chave_valida
from app.core.database import get_db
from app.models import Conferencia, Evento, Filial, NotaFiscal, Usuario

router = APIRouter(prefix="/conferencias", tags=["conferencias"])

ATIVAS = ("EM_ANDAMENTO", "PAUSADA")


class AbrirIn(BaseModel):
    chave: str
    filial_id: int
    dispositivo: str = "desconhecido"

    @field_validator("chave")
    @classmethod
    def validar_chave(cls, v: str) -> str:
        v = v.strip()
        if not chave_valida(v):
            raise ValueError("Chave de acesso inválida")
        return v


class ConferenciaOut(BaseModel):
    id: int
    chave: str
    status: str
    filial_id: int
    iniciada_em: datetime
    nota_encontrada: bool
    retomada: bool = False


def _saida(conf: Conferencia, retomada: bool = False) -> ConferenciaOut:
    return ConferenciaOut(
        id=conf.id,
        chave=conf.chave,
        status=conf.status,
        filial_id=conf.filial_id,
        iniciada_em=conf.iniciada_em,
        nota_encontrada=conf.nota_id is not None,
        retomada=retomada,
    )


@router.post("", response_model=ConferenciaOut)
def abrir(
    dados: AbrirIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    filial = db.get(Filial, dados.filial_id)
    if filial is None or not filial.ativa:
        raise HTTPException(422, "Filial inválida")

    existente = db.scalar(
        select(Conferencia).where(Conferencia.chave == dados.chave, Conferencia.rodada == 1)
    )
    if existente:
        if existente.operador_id == usuario.id and existente.status in ATIVAS:
            return _saida(existente, retomada=True)
        raise HTTPException(409, "Esta nota já tem uma conferência aberta ou concluída")

    nota_id = db.scalar(select(NotaFiscal.id).where(NotaFiscal.chave == dados.chave))
    conf = Conferencia(
        chave=dados.chave,
        nota_id=nota_id,
        operador_id=usuario.id,
        filial_id=filial.id,
        status="EM_ANDAMENTO",
    )
    db.add(conf)
    try:
        db.flush()
        db.add(
            Evento(
                evento_uuid=uuid.uuid4(),
                conferencia_id=conf.id,
                tipo="INICIO",
                dados={},
                origem="sistema",
                ts_dispositivo=datetime.now(timezone.utc),
                usuario_id=usuario.id,
                dispositivo=dados.dispositivo,
                filial_id=filial.id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Esta nota já tem uma conferência aberta ou concluída")
    db.refresh(conf)
    return _saida(conf)


@router.get("/{conferencia_id}", response_model=ConferenciaOut)
def obter(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    conf = db.get(Conferencia, conferencia_id)
    if conf is None:
        raise HTTPException(404, "Conferência não encontrada")
    if conf.operador_id != usuario.id and usuario.perfil not in ("supervisor", "admin"):
        raise HTTPException(403, "Sem permissão")
    return _saida(conf)
