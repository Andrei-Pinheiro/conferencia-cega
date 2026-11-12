import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import usuario_atual
from app.core.database import get_db
from app.models import Conferencia, Evento, NotaFiscal, Usuario
from app.services.contagem import EventoContagem, consolidar

router = APIRouter(prefix="/conferencias", tags=["eventos"])

LIMITE_QUANTIDADE = Decimal("999999")


class EventoIn(BaseModel):
    evento_uuid: uuid.UUID
    tipo: Literal["LEITURA", "ENTRADA_MANUAL", "ESTORNO", "PAUSA", "RETOMADA", "FIM"]
    origem: Literal["leitor", "camera", "manual"]
    ts_dispositivo: AwareDatetime
    dispositivo: str = Field(min_length=1, max_length=100)
    dados: dict = Field(default_factory=dict)


class EventoOut(BaseModel):
    evento_uuid: uuid.UUID
    tipo: str
    origem: str
    ts_dispositivo: datetime
    dados: dict


class RespostaEvento(BaseModel):
    evento_uuid: uuid.UUID
    duplicado: bool
    status: str


class ItemContagem(BaseModel):
    codigo: str
    quantidade: Decimal


class ContagemOut(BaseModel):
    itens: list[ItemContagem]
    total_eventos: int


def _conferencia(db: Session, conferencia_id: int, bloquear: bool = False) -> Conferencia:
    consulta = select(Conferencia).where(Conferencia.id == conferencia_id)
    if bloquear:
        consulta = consulta.with_for_update()
    conf = db.scalar(consulta)
    if conf is None:
        raise HTTPException(404, "Conferência não encontrada")
    return conf


def _exigir_leitura(conf: Conferencia, usuario: Usuario) -> None:
    if conf.operador_id != usuario.id and usuario.perfil not in ("supervisor", "admin"):
        raise HTTPException(403, "Sem permissão")


def _codigo(dados: dict) -> str:
    codigo = str(dados.get("codigo", "")).strip()
    if not codigo or len(codigo) > 60:
        raise HTTPException(422, "Código do produto inválido")
    return codigo


def _quantidade(valor) -> Decimal:
    try:
        q = Decimal(str(valor))
    except InvalidOperation:
        raise HTTPException(422, "Quantidade inválida")
    if not q.is_finite() or q <= 0 or q > LIMITE_QUANTIDADE:
        raise HTTPException(422, "Quantidade inválida")
    return q


def _validar(ev: EventoIn, conf: Conferencia, db: Session) -> dict:
    """Confere o estado da conferência e o conteúdo do evento. Devolve o 'dados' a gravar."""
    if ev.tipo == "RETOMADA":
        if conf.status != "PAUSADA":
            raise HTTPException(409, "A conferência não está pausada")
    elif ev.tipo == "FIM":
        if conf.status not in ("EM_ANDAMENTO", "PAUSADA"):
            raise HTTPException(409, "A conferência já foi finalizada")
    elif conf.status != "EM_ANDAMENTO":
        raise HTTPException(409, "A conferência não está em andamento")

    if ev.tipo == "LEITURA":
        return {"codigo": _codigo(ev.dados)}

    if ev.tipo == "ENTRADA_MANUAL":
        quantidade = _quantidade(ev.dados.get("quantidade"))
        confirmacao = _quantidade(ev.dados.get("confirmacao"))
        if quantidade != confirmacao:
            raise HTTPException(422, "As quantidades digitadas não conferem")
        return {
            "codigo": _codigo(ev.dados),
            "quantidade": str(quantidade),
            "confirmacao": str(confirmacao),
        }

    if ev.tipo == "ESTORNO":
        try:
            alvo = uuid.UUID(str(ev.dados.get("evento_uuid_estornado")))
        except ValueError:
            raise HTTPException(422, "Evento a estornar inválido")
        original = db.scalar(
            select(Evento).where(
                Evento.evento_uuid == alvo,
                Evento.conferencia_id == conf.id,
                Evento.tipo.in_(("LEITURA", "ENTRADA_MANUAL")),
            )
        )
        if original is None:
            raise HTTPException(422, "Evento a estornar não encontrado nesta conferência")
        ja_estornados = {
            str(e.dados.get("evento_uuid_estornado"))
            for e in db.scalars(
                select(Evento).where(Evento.conferencia_id == conf.id, Evento.tipo == "ESTORNO")
            )
        }
        if str(alvo) in ja_estornados:
            raise HTTPException(409, "Este evento já foi estornado")
        return {
            "evento_uuid_estornado": str(alvo),
            "motivo": str(ev.dados.get("motivo", ""))[:200],
        }

    return {}  # PAUSA, RETOMADA, FIM


@router.post("/{conferencia_id}/eventos", response_model=RespostaEvento)
def registrar(
    conferencia_id: int,
    ev: EventoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    conf = _conferencia(db, conferencia_id, bloquear=True)
    if conf.operador_id != usuario.id:
        raise HTTPException(403, "Só o operador da conferência registra eventos")

    # Idempotência: o mesmo evento enviado de novo (rede instável) não grava duas vezes.
    existente = db.scalar(select(Evento).where(Evento.evento_uuid == ev.evento_uuid))
    if existente:
        if existente.conferencia_id != conf.id:
            raise HTTPException(409, "Identificador de evento já usado")
        return RespostaEvento(evento_uuid=ev.evento_uuid, duplicado=True, status=conf.status)

    dados = _validar(ev, conf, db)

    db.add(
        Evento(
            evento_uuid=ev.evento_uuid,
            conferencia_id=conf.id,
            tipo=ev.tipo,
            dados=dados,
            origem=ev.origem,
            ts_dispositivo=ev.ts_dispositivo,
            usuario_id=usuario.id,
            dispositivo=ev.dispositivo,
            filial_id=conf.filial_id,
        )
    )
    if ev.tipo == "PAUSA":
        conf.status = "PAUSADA"
    elif ev.tipo == "RETOMADA":
        conf.status = "EM_ANDAMENTO"
    elif ev.tipo == "FIM":
        if conf.nota_id is None:
            conf.nota_id = db.scalar(select(NotaFiscal.id).where(NotaFiscal.chave == conf.chave))
        conf.status = "FINALIZADA" if conf.nota_id else "AGUARDANDO_NF"
        conf.finalizada_em = datetime.now(timezone.utc)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RespostaEvento(evento_uuid=ev.evento_uuid, duplicado=True, status=conf.status)
    return RespostaEvento(evento_uuid=ev.evento_uuid, duplicado=False, status=conf.status)


@router.get("/{conferencia_id}/eventos", response_model=list[EventoOut])
def listar(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    conf = _conferencia(db, conferencia_id)
    _exigir_leitura(conf, usuario)
    return db.scalars(
        select(Evento).where(Evento.conferencia_id == conf.id).order_by(Evento.id)
    ).all()


@router.get("/{conferencia_id}/contagem", response_model=ContagemOut)
def contagem(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_atual),
):
    conf = _conferencia(db, conferencia_id)
    _exigir_leitura(conf, usuario)
    eventos = db.scalars(
        select(Evento).where(Evento.conferencia_id == conf.id).order_by(Evento.id)
    ).all()
    total = consolidar([EventoContagem(str(e.evento_uuid), e.tipo, e.dados) for e in eventos])
    return ContagemOut(
        itens=[ItemContagem(codigo=c, quantidade=q) for c, q in sorted(total.items())],
        total_eventos=len(eventos),
    )
