import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import gerar_hash
from app.models import Usuario


def main():
    login = input("Login do admin: ").strip()
    nome = input("Nome: ").strip()
    senha = getpass.getpass("Senha (mínimo 8 caracteres): ")
    confirma = getpass.getpass("Confirme a senha: ")

    if len(senha) < 8 or senha != confirma:
        print("Senha inválida ou diferente da confirmação.")
        return

    with SessionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.login == login)):
            print("Esse login já existe.")
            return
        db.add(Usuario(login=login, nome=nome, senha_hash=gerar_hash(senha), perfil="admin"))
        db.commit()
    print("Admin criado com sucesso.")


if __name__ == "__main__":
    main()
