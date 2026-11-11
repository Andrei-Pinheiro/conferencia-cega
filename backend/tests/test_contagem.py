from decimal import Decimal

from app.services.contagem import EventoContagem, consolidar


def leitura(uid, codigo):
    return EventoContagem(uid, "LEITURA", {"codigo": codigo})


def manual(uid, codigo, qtd):
    return EventoContagem(uid, "ENTRADA_MANUAL", {"codigo": codigo, "quantidade": qtd})


def estorno(uid, alvo):
    return EventoContagem(uid, "ESTORNO", {"evento_uuid_estornado": alvo})


def test_leituras_repetidas_somam():
    eventos = [leitura("1", "A"), leitura("2", "A"), leitura("3", "A")]
    assert consolidar(eventos) == {"A": Decimal(3)}


def test_leitura_e_entrada_manual_somam():
    eventos = [leitura("1", "A"), leitura("2", "A"), manual("3", "A", "12")]
    assert consolidar(eventos) == {"A": Decimal(14)}


def test_codigos_diferentes_ficam_separados():
    eventos = [leitura("1", "A"), leitura("2", "B"), leitura("3", "B")]
    assert consolidar(eventos) == {"A": Decimal(1), "B": Decimal(2)}


def test_estorno_anula_uma_leitura():
    eventos = [leitura("1", "A"), leitura("2", "A"), leitura("3", "A"), estorno("4", "2")]
    assert consolidar(eventos) == {"A": Decimal(2)}


def test_estorno_de_entrada_manual_remove_o_codigo():
    eventos = [manual("1", "A", "5"), estorno("2", "1")]
    assert consolidar(eventos) == {}


def test_estorno_nao_apaga_o_evento_original():
    eventos = [leitura("1", "A"), estorno("2", "1")]
    consolidar(eventos)
    assert len(eventos) == 2 and eventos[0].tipo == "LEITURA"


def test_ordem_dos_eventos_nao_importa():
    eventos = [estorno("2", "1"), leitura("1", "A"), leitura("3", "A")]
    assert consolidar(eventos) == {"A": Decimal(1)}


def test_estorno_repetido_conta_uma_vez():
    eventos = [leitura("1", "A"), leitura("2", "A"), estorno("3", "1"), estorno("4", "1")]
    assert consolidar(eventos) == {"A": Decimal(1)}


def test_quantidade_decimal():
    eventos = [manual("1", "A", "2.5"), manual("2", "A", "0.5")]
    assert consolidar(eventos) == {"A": Decimal("3.0")}


def test_eventos_de_controle_nao_contam():
    eventos = [
        EventoContagem("1", "INICIO", {}),
        leitura("2", "A"),
        EventoContagem("3", "PAUSA", {}),
        EventoContagem("4", "RETOMADA", {}),
        EventoContagem("5", "FIM", {}),
    ]
    assert consolidar(eventos) == {"A": Decimal(1)}
