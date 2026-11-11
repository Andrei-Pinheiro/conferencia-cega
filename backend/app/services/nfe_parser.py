from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.core.chave import chave_valida
from app.core.cnpj import limpar_cnpj


class XmlInvalido(ValueError):
    """XML que não é uma NF-e válida ou está incompleto."""


@dataclass
class LoteParseado:
    lote: str
    quantidade: Decimal
    fabricacao: date | None
    validade: date | None


@dataclass
class ItemParseado:
    numero_item: int
    codigo: str
    ean: str | None
    descricao: str
    unidade_comercial: str
    quantidade_comercial: Decimal
    ean_tributavel: str | None
    unidade_tributavel: str
    quantidade_tributavel: Decimal
    lotes: list[LoteParseado] = field(default_factory=list)


@dataclass
class NotaParseada:
    chave: str
    numero: str
    serie: str
    emitente_cnpj: str
    emitente_nome: str
    destinatario_cnpj: str
    destinatario_nome: str
    emissao: datetime
    itens: list[ItemParseado]
    avisos: list[str] = field(default_factory=list)


def _remover_namespaces(raiz) -> None:
    for no in raiz.iter():
        if isinstance(no.tag, str) and "}" in no.tag:
            no.tag = no.tag.split("}", 1)[1]


def _texto(no, caminho: str) -> str | None:
    achado = no.find(caminho) if no is not None else None
    if achado is None or achado.text is None:
        return None
    return achado.text.strip()


def _obrigatorio(no, caminho: str) -> str:
    valor = _texto(no, caminho)
    if not valor:
        raise XmlInvalido(f"Campo obrigatório ausente no XML: {caminho}")
    return valor


def _decimal(valor: str, campo: str) -> Decimal:
    try:
        return Decimal(valor)
    except (InvalidOperation, TypeError):
        raise XmlInvalido(f"Valor numérico inválido em {campo}: {valor!r}")


def _ean(valor: str | None) -> str | None:
    # "SEM GTIN" e similares viram None
    if valor and valor.isdigit() and len(valor) in (8, 12, 13, 14):
        return valor
    return None


def _data(valor: str | None, descricao: str, avisos: list[str]) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        avisos.append(f"{descricao}: data inválida no XML ({valor!r})")
        return None


def interpretar_xml(conteudo: bytes | str) -> NotaParseada:
    """Lê o XML de uma NF-e e devolve os dados estruturados. Função pura: sem banco."""
    try:
        raiz = fromstring(conteudo)
    except (ParseError, DefusedXmlException) as erro:
        raise XmlInvalido(f"XML inválido: {erro}")

    _remover_namespaces(raiz)
    inf = raiz if raiz.tag == "infNFe" else raiz.find(".//infNFe")
    if inf is None:
        raise XmlInvalido("Não é uma NF-e: elemento infNFe não encontrado")

    chave = (inf.get("Id") or "").removeprefix("NFe")
    if not chave:
        chave = _texto(raiz, ".//protNFe/infProt/chNFe") or ""
    if not chave_valida(chave):
        raise XmlInvalido(f"Chave de acesso inválida: {chave!r}")

    ide = inf.find("ide")
    emit = inf.find("emit")
    dest = inf.find("dest")
    if ide is None or emit is None or dest is None:
        raise XmlInvalido("XML sem ide, emit ou dest")

    emissao_txt = _texto(ide, "dhEmi")
    if emissao_txt is None:
        dia = _obrigatorio(ide, "dEmi")
        emissao_txt = f"{dia}T00:00:00-03:00"
    try:
        emissao = datetime.fromisoformat(emissao_txt)
    except ValueError:
        raise XmlInvalido(f"Data de emissão inválida: {emissao_txt!r}")

    avisos: list[str] = []
    itens: list[ItemParseado] = []

    for det in inf.findall("det"):
        prod = det.find("prod")
        if prod is None:
            raise XmlInvalido("Item sem o elemento prod")
        try:
            numero_item = int(det.get("nItem", ""))
        except ValueError:
            raise XmlInvalido("Item sem número (nItem)")

        item = ItemParseado(
            numero_item=numero_item,
            codigo=_obrigatorio(prod, "cProd"),
            ean=_ean(_texto(prod, "cEAN")),
            descricao=_obrigatorio(prod, "xProd"),
            unidade_comercial=_obrigatorio(prod, "uCom"),
            quantidade_comercial=_decimal(_obrigatorio(prod, "qCom"), f"qCom do item {numero_item}"),
            ean_tributavel=_ean(_texto(prod, "cEANTrib")),
            unidade_tributavel=_obrigatorio(prod, "uTrib"),
            quantidade_tributavel=_decimal(_obrigatorio(prod, "qTrib"), f"qTrib do item {numero_item}"),
        )

        for rastro in prod.findall("rastro"):
            item.lotes.append(
                LoteParseado(
                    lote=_obrigatorio(rastro, "nLote"),
                    quantidade=_decimal(_obrigatorio(rastro, "qLote"), f"qLote do item {numero_item}"),
                    fabricacao=_data(_texto(rastro, "dFab"), f"Item {numero_item}, fabricação", avisos),
                    validade=_data(_texto(rastro, "dVal"), f"Item {numero_item}, validade", avisos),
                )
            )

        if (
            item.unidade_comercial.upper() != item.unidade_tributavel.upper()
            or item.quantidade_comercial != item.quantidade_tributavel
        ):
            avisos.append(
                f"Item {numero_item}: unidade comercial ({item.unidade_comercial} "
                f"{item.quantidade_comercial}) difere da tributável "
                f"({item.unidade_tributavel} {item.quantidade_tributavel})"
            )
        itens.append(item)

    if not itens:
        raise XmlInvalido("NF-e sem itens")

    return NotaParseada(
        chave=chave,
        numero=_obrigatorio(ide, "nNF"),
        serie=_obrigatorio(ide, "serie"),
        emitente_cnpj=limpar_cnpj(_obrigatorio(emit, "CNPJ")),
        emitente_nome=_obrigatorio(emit, "xNome"),
        destinatario_cnpj=limpar_cnpj(_obrigatorio(dest, "CNPJ")),
        destinatario_nome=_obrigatorio(dest, "xNome"),
        emissao=emissao,
        itens=itens,
        avisos=avisos,
    )
