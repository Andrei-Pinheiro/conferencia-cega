from fastapi import FastAPI
from sqlalchemy import text

from app.api import auth, filiais, usuarios
from app.core.database import engine

app = FastAPI(title="Conferência Cega de NF")
app.include_router(auth.router)
app.include_router(filiais.router)
app.include_router(usuarios.router)


@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/saude/db")
def saude_db():
    with engine.connect() as conn:
        versao = conn.execute(text("select version()")).scalar()
    return {"status": "ok", "postgres": versao}
