from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_perfil, usuario_atual
from app.core.cnpj import cnpj_valido, limpar_cnpj
from app.core.database import get_db
from app.models import Filial

router = APIRouter(prefix="/filiais", tags=["filiais"])


class FilialIn(BaseModel):
    nome: str
    cnpj: str

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        if not cnpj_valido(v):
            raise ValueError("CNPJ inválido")
        return limpar_cnpj(v)


class FilialUpdate(BaseModel):
    nome: str | None = None
    ativa: bool | None = None


class FilialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    cnpj: str
    ativa: bool


@router.get("", response_model=list[FilialOut])
def listar(db: Session = Depends(get_db), _=Depends(usuario_atual)):
    return db.scalars(select(Filial).order_by(Filial.nome)).all()


@router.post("", response_model=FilialOut, status_code=201)
def criar(dados: FilialIn, db: Session = Depends(get_db), _=Depends(exigir_perfil("admin"))):
    if db.scalar(select(Filial).where(Filial.cnpj == dados.cnpj)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe filial com esse CNPJ")
    filial = Filial(nome=dados.nome.strip(), cnpj=dados.cnpj)
    db.add(filial)
    db.commit()
    db.refresh(filial)
    return filial


@router.patch("/{filial_id}", response_model=FilialOut)
def atualizar(
    filial_id: int,
    dados: FilialUpdate,
    db: Session = Depends(get_db),
    _=Depends(exigir_perfil("admin")),
):
    filial = db.get(Filial, filial_id)
    if filial is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Filial não encontrada")
    if dados.nome is not None:
        filial.nome = dados.nome.strip()
    if dados.ativa is not None:
        filial.ativa = dados.ativa
    db.commit()
    db.refresh(filial)
    return filial
