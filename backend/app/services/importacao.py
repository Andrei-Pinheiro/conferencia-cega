from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Filial, ItemNota, LoteItem, NotaFiscal
from app.services.nfe_parser import NotaParseada

# Na V1 só entram transferências entre filiais. Relaxar quando entrarem fornecedores.
EXIGIR_FILIAIS_CADASTRADAS = True


class ImportacaoRecusada(ValueError):
    """A nota é válida, mas não pode ser importada (ex.: CNPJ que não é filial)."""


def _buscar(db: Session, chave: str) -> NotaFiscal | None:
    return db.scalar(select(NotaFiscal).where(NotaFiscal.chave == chave))


def importar_nota(
    db: Session, nota: NotaParseada, xml: bytes, origem: str
) -> tuple[NotaFiscal, bool]:
    """Grava a cópia da NF no banco próprio. Devolve (registro, foi_criada).

    Se a chave já existe, devolve a cópia que já está lá sem alterá-la:
    ela é o retrato do esperado e não muda depois.
    """
    existente = _buscar(db, nota.chave)
    if existente:
        return existente, False

    if EXIGIR_FILIAIS_CADASTRADAS:
        cnpjs = {nota.emitente_cnpj, nota.destinatario_cnpj}
        cadastrados = set(db.scalars(select(Filial.cnpj).where(Filial.cnpj.in_(cnpjs))))
        faltando = cnpjs - cadastrados
        if faltando:
            raise ImportacaoRecusada(
                "CNPJ não cadastrado como filial: " + ", ".join(sorted(faltando))
            )

    registro = NotaFiscal(
        chave=nota.chave,
        numero=nota.numero,
        serie=nota.serie,
        emitente_cnpj=nota.emitente_cnpj,
        emitente_nome=nota.emitente_nome,
        destinatario_cnpj=nota.destinatario_cnpj,
        destinatario_nome=nota.destinatario_nome,
        emissao=nota.emissao,
        xml_original=xml.decode("utf-8", errors="replace"),
        origem=origem,
    )
    for it in nota.itens:
        registro.itens.append(
            ItemNota(
                numero_item=it.numero_item,
                codigo=it.codigo,
                ean=it.ean,
                descricao=it.descricao,
                unidade_comercial=it.unidade_comercial,
                quantidade_comercial=it.quantidade_comercial,
                ean_tributavel=it.ean_tributavel,
                unidade_tributavel=it.unidade_tributavel,
                quantidade_tributavel=it.quantidade_tributavel,
                lotes=[
                    LoteItem(
                        lote=l.lote,
                        quantidade=l.quantidade,
                        fabricacao=l.fabricacao,
                        validade=l.validade,
                    )
                    for l in it.lotes
                ],
            )
        )

    db.add(registro)
    try:
        db.commit()
    except IntegrityError:
        # duas importações simultâneas da mesma chave: vale a primeira
        db.rollback()
        return _buscar(db, nota.chave), False
    db.refresh(registro)
    return registro, True
