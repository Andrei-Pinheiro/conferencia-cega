import re

_PESOS = [2, 3, 4, 5, 6, 7, 8, 9]


def calcular_dv(base43: str) -> int:
    soma = sum(int(d) * _PESOS[i % 8] for i, d in enumerate(reversed(base43)))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def chave_valida(chave: str) -> bool:
    return bool(re.fullmatch(r"\d{44}", chave)) and calcular_dv(chave[:43]) == int(chave[43])
