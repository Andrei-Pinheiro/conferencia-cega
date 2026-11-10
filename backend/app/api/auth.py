from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import usuario_atual
from app.core.database import get_db
from app.core.security import criar_token, verificar_senha
from app.models import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    login: str
    senha: str


@router.post("/login")
def login(dados: LoginIn, db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.login == dados.login))
    if (
        usuario is None
        or not usuario.ativo
        or not verificar_senha(dados.senha, usuario.senha_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login ou senha incorretos")
    return {"access_token": criar_token(usuario.id, usuario.perfil), "token_type": "bearer"}


@router.get("/me")
def me(usuario: Usuario = Depends(usuario_atual)):
    return {
        "id": usuario.id,
        "login": usuario.login,
        "nome": usuario.nome,
        "perfil": usuario.perfil,
    }
