from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_perfil, usuario_atual
from app.core.database import get_db
from app.models import NotaFiscal
from app.services.importacao import ImportacaoRecusada, importar_nota
from app.services.nfe_parser import XmlInvalido, interpretar_xml

router = APIRouter(prefix="/notas", tags=["notas"])

LIMITE_BYTES = 2 * 1024 * 1024  # 2 MB por XML


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lote: str
    quantidade: Decimal
    fabricacao: date | None
    validade: date | None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    numero_item: int
    codigo: str
    ean: str | None
    descricao: str
    unidade_comercial: str
    quantidade_comercial: Decimal
    unidade_tributavel: str
    quantidade_tributavel: Decimal
    lotes: list[LoteOut]


class NotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    chave: str
    numero: str
    serie: str
    emitente_cnpj: str
    emitente_nome: str
    destinatario_cnpj: str
    destinatario_nome: str
    emissao: datetime
    origem: str
    itens: list[ItemOut]


@router.post("/upload", status_code=201)
def upload(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(usuario_atual),
):
    """Importa um XML de NF-e. A resposta não traz itens nem quantidades (contagem cega)."""
    conteudo = arquivo.file.read(LIMITE_BYTES + 1)
    if len(conteudo) > LIMITE_BYTES:
        raise HTTPException(413, "Arquivo maior que 2 MB")
    try:
        nota = interpretar_xml(conteudo)
        registro, criada = importar_nota(db, nota, conteudo, "upload")
    except (XmlInvalido, ImportacaoRecusada) as erro:
        raise HTTPException(422, str(erro))
    return {"chave": registro.chave, "numero": registro.numero, "ja_existia": not criada}


@router.get("/{chave}", response_model=NotaOut)
def detalhe(
    chave: str,
    db: Session = Depends(get_db),
    _=Depends(exigir_perfil("supervisor", "admin")),
):
    nota = db.scalar(select(NotaFiscal).where(NotaFiscal.chave == chave))
    if nota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota não encontrada")
    return nota
