from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_perfil
from app.core.database import get_db
from app.core.security import gerar_hash
from app.models import Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

Perfil = Literal["conferente", "supervisor", "admin"]


class UsuarioIn(BaseModel):
    login: str
    nome: str
    senha: str = Field(min_length=8)
    perfil: Perfil


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    perfil: Perfil | None = None
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=8)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    login: str
    nome: str
    perfil: str
    ativo: bool


@router.get("", response_model=list[UsuarioOut])
def listar(db: Session = Depends(get_db), _=Depends(exigir_perfil("admin"))):
    return db.scalars(select(Usuario).order_by(Usuario.login)).all()


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(dados: UsuarioIn, db: Session = Depends(get_db), _=Depends(exigir_perfil("admin"))):
    login = dados.login.strip()
    if db.scalar(select(Usuario).where(Usuario.login == login)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esse login já existe")
    usuario = Usuario(
        login=login,
        nome=dados.nome.strip(),
        senha_hash=gerar_hash(dados.senha),
        perfil=dados.perfil,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def atualizar(
    usuario_id: int,
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(exigir_perfil("admin")),
):
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    if usuario.id == admin.id and (dados.ativo is False or (dados.perfil and dados.perfil != "admin")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Você não pode desativar ou rebaixar a si mesmo")
    if dados.nome is not None:
        usuario.nome = dados.nome.strip()
    if dados.perfil is not None:
        usuario.perfil = dados.perfil
    if dados.ativo is not None:
        usuario.ativo = dados.ativo
    if dados.senha is not None:
        usuario.senha_hash = gerar_hash(dados.senha)
    db.commit()
    db.refresh(usuario)
    return usuario
