from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_hasher = PasswordHash.recommended()


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return _hasher.verify(senha, senha_hash)


def criar_token(usuario_id: int, perfil: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expira_minutos)
    dados = {"sub": str(usuario_id), "perfil": perfil, "exp": expira}
    return jwt.encode(dados, settings.secret_key, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
