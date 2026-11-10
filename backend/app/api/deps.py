import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decodificar_token
from app.models import Usuario

bearer = HTTPBearer()


def usuario_atual(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    erro = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas ou sessão expirada")
    try:
        dados = decodificar_token(cred.credentials)
    except jwt.PyJWTError:
        raise erro
    usuario = db.get(Usuario, int(dados["sub"]))
    if usuario is None or not usuario.ativo:
        raise erro
    return usuario


def exigir_perfil(*perfis: str):
    def verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão")
        return usuario

    return verificar
