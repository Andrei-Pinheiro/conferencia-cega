from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EventoContagem:
    evento_uuid: str
    tipo: str
    dados: dict


def _contribuicao(evento: EventoContagem) -> tuple[str, Decimal] | None:
    """Quanto este evento soma na contagem: (código, quantidade), ou None se não conta."""
    if evento.tipo == "LEITURA":
        return evento.dados["codigo"], Decimal(1)
    if evento.tipo == "ENTRADA_MANUAL":
        return evento.dados["codigo"], Decimal(str(evento.dados["quantidade"]))
    return None


def consolidar(eventos: list[EventoContagem]) -> dict[str, Decimal]:
    """Calcula a contagem a partir dos eventos. Função pura: não altera nada.

    Cada LEITURA vale 1 e cada ENTRADA_MANUAL vale a quantidade digitada.
    Um ESTORNO anula o evento que ele aponta; o evento original continua existindo.
    A ordem dos eventos não importa.
    """
    contribuicoes: dict[str, tuple[str, Decimal]] = {}
    estornados: set[str] = set()

    for e in eventos:
        if e.tipo == "ESTORNO":
            estornados.add(str(e.dados["evento_uuid_estornado"]))
            continue
        item = _contribuicao(e)
        if item is not None:
            contribuicoes[str(e.evento_uuid)] = item

    total: dict[str, Decimal] = defaultdict(Decimal)
    for uid, (codigo, quantidade) in contribuicoes.items():
        if uid not in estornados:
            total[codigo] += quantidade
    return {codigo: q for codigo, q in total.items() if q != 0}
