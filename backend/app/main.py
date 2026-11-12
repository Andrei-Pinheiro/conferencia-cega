from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import auth, conferencias, eventos, filiais, notas, usuarios
from app.core.database import engine

app = FastAPI(title="Conferência Cega de NF")
app.include_router(auth.router)
app.include_router(filiais.router)
app.include_router(usuarios.router)
app.include_router(notas.router)
app.include_router(conferencias.router)
app.include_router(eventos.router)


@app.get("/saude")
def saude():
    return {"status": "ok"}


@app.get("/saude/db")
def saude_db():
    with engine.connect() as conn:
        versao = conn.execute(text("select version()")).scalar()
    return {"status": "ok", "postgres": versao}


# Telas (HTML/CSS/JS puros), servidas pela própria API
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/shared", StaticFiles(directory=FRONTEND / "shared"), name="shared")
app.mount("/conferente", StaticFiles(directory=FRONTEND / "conferente", html=True), name="conferente")
