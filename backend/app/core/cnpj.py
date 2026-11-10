import re

_PESOS1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS2 = [6] + _PESOS1


def limpar_cnpj(valor: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


def _dv(caracteres: str, pesos: list[int]) -> int:
    soma = sum((ord(c) - 48) * p for c, p in zip(caracteres, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(valor: str) -> bool:
    cnpj = limpar_cnpj(valor)
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj) or cnpj == cnpj[0] * 14:
        return False
    d1 = _dv(cnpj[:12], _PESOS1)
    d2 = _dv(cnpj[:12] + str(d1), _PESOS2)
    return cnpj[12:] == f"{d1}{d2}"
