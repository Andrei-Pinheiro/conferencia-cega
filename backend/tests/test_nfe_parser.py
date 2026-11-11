from decimal import Decimal
from pathlib import Path

import pytest

from app.core.chave import calcular_dv, chave_valida
from app.services.nfe_parser import XmlInvalido, interpretar_xml

BASE43 = "3526111122233300018155001000000123112345678"
CHAVE = BASE43 + str(calcular_dv(BASE43))

XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{CHAVE}" versao="4.00">
      <ide><nNF>123</nNF><serie>1</serie><dhEmi>2026-11-05T10:30:00-03:00</dhEmi></ide>
      <emit><CNPJ>11222333000181</CNPJ><xNome>Filial Origem</xNome></emit>
      <dest><CNPJ>11444777000161</CNPJ><xNome>Filial Destino</xNome></dest>
      <det nItem="1">
        <prod>
          <cProd>A100</cProd><cEAN>7891234567895</cEAN><xProd>Produto A</xProd>
          <uCom>CX</uCom><qCom>10.0000</qCom>
          <cEANTrib>7891234567895</cEANTrib><uTrib>CX</uTrib><qTrib>10.0000</qTrib>
          <rastro><nLote>L1</nLote><qLote>6.000</qLote><dFab>2026-01-10</dFab><dVal>2027-01-10</dVal></rastro>
          <rastro><nLote>L2</nLote><qLote>4.000</qLote><dFab>2026-02-10</dFab><dVal>2027-02-10</dVal></rastro>
        </prod>
      </det>
      <det nItem="2">
        <prod>
          <cProd>B200</cProd><cEAN>SEM GTIN</cEAN><xProd>Produto B</xProd>
          <uCom>CX</uCom><qCom>2.0000</qCom>
          <cEANTrib>SEM GTIN</cEANTrib><uTrib>UN</uTrib><qTrib>24.0000</qTrib>
        </prod>
      </det>
      <det nItem="3">
        <prod>
          <cProd>A100</cProd><cEAN>7891234567895</cEAN><xProd>Produto A</xProd>
          <uCom>CX</uCom><qCom>5.0000</qCom>
          <cEANTrib>7891234567895</cEANTrib><uTrib>CX</uTrib><qTrib>5.0000</qTrib>
        </prod>
      </det>
    </infNFe>
    <protNFe><infProt><chNFe>{CHAVE}</chNFe></infProt></protNFe>
  </NFe>
</nfeProc>"""


def test_chave_valida():
    assert chave_valida(CHAVE)
    assert not chave_valida(CHAVE[:-1] + str((int(CHAVE[-1]) + 1) % 10))
    assert not chave_valida("123")


def test_cabecalho():
    nota = interpretar_xml(XML.encode())
    assert nota.chave == CHAVE
    assert nota.numero == "123" and nota.serie == "1"
    assert nota.emitente_cnpj == "11222333000181"
    assert nota.destinatario_cnpj == "11444777000161"
    assert nota.emissao.year == 2026 and nota.emissao.utcoffset() is not None


def test_itens_e_lotes():
    nota = interpretar_xml(XML.encode())
    assert len(nota.itens) == 3
    a = nota.itens[0]
    assert a.quantidade_comercial == Decimal("10")
    assert [l.lote for l in a.lotes] == ["L1", "L2"]
    assert sum(l.quantidade for l in a.lotes) == Decimal("10")
    assert a.lotes[0].validade.isoformat() == "2027-01-10"


def test_item_repetido_continua_separado():
    nota = interpretar_xml(XML.encode())
    assert [i.codigo for i in nota.itens].count("A100") == 2


def test_sem_gtin_vira_none():
    assert interpretar_xml(XML.encode()).itens[1].ean is None


def test_aviso_unidade_diferente():
    nota = interpretar_xml(XML.encode())
    assert len(nota.avisos) == 1 and "Item 2" in nota.avisos[0]


def test_chave_invalida():
    ruim = XML.replace(CHAVE, CHAVE[:-1] + str((int(CHAVE[-1]) + 1) % 10))
    with pytest.raises(XmlInvalido):
        interpretar_xml(ruim.encode())


def test_xml_quebrado():
    with pytest.raises(XmlInvalido):
        interpretar_xml(b"<nfeProc><NFe>")


def test_xml_com_entidade_e_rejeitado():
    perigoso = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>'
    with pytest.raises(XmlInvalido):
        interpretar_xml(perigoso)


ARQUIVOS_REAIS = sorted((Path(__file__).parent / "xmls_reais").glob("*.xml"))


@pytest.mark.parametrize("caminho", ARQUIVOS_REAIS, ids=lambda p: p.name)
def test_xml_real_interpreta(caminho):
    nota = interpretar_xml(caminho.read_bytes())
    assert nota.itens
    print(f"\n{caminho.name}: {len(nota.itens)} itens, avisos: {nota.avisos}")
