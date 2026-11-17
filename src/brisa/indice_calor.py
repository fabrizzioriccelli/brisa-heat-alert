"""Cálculo do Índice de Calor (Heat Index) e classificação de risco.

Implementa o algoritmo publicado pelo Weather Prediction Center (NWS/NOAA):
fórmula simples de Steadman e, quando o resultado médio passa de 80 °F,
a regressão de Rothfusz (1990) com os dois ajustes oficiais.
"""
import math

from .config import FAIXAS_IC


def celsius_para_fahrenheit(c: float) -> float:
    return c * 9 / 5 + 32


def fahrenheit_para_celsius(f: float) -> float:
    return (f - 32) * 5 / 9


def indice_de_calor(temp_c: float, umidade: float) -> float:
    """Retorna o índice de calor em °C a partir da temperatura (°C) e UR (%).

    Levanta ValueError para entradas fisicamente impossíveis.
    """
    if temp_c is None or umidade is None:
        raise ValueError("Temperatura e umidade são obrigatórias.")
    if not (-50 <= temp_c <= 60):
        raise ValueError(f"Temperatura fora da faixa plausível: {temp_c} °C")
    if not (0 <= umidade <= 100):
        raise ValueError(f"Umidade relativa deve estar entre 0 e 100: {umidade}")

    t = celsius_para_fahrenheit(temp_c)
    ur = umidade

    # 1) Fórmula simples (Steadman); vale quando a média com T fica abaixo de 80 °F
    simples = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + ur * 0.094)
    if (simples + t) / 2 < 80:
        return round(fahrenheit_para_celsius(simples), 2)

    # 2) Regressão de Rothfusz
    ic = (-42.379 + 2.04901523 * t + 10.14333127 * ur
          - 0.22475541 * t * ur - 0.00683783 * t * t
          - 0.05481717 * ur * ur + 0.00122874 * t * t * ur
          + 0.00085282 * t * ur * ur - 0.00000199 * t * t * ur * ur)

    # 3) Ajustes oficiais
    if ur < 13 and 80 <= t <= 112:
        ic -= ((13 - ur) / 4) * math.sqrt((17 - abs(t - 95.0)) / 17)
    elif ur > 85 and 80 <= t <= 87:
        ic += ((ur - 85) / 10) * ((87 - t) / 5)

    return round(fahrenheit_para_celsius(ic), 2)


def classificar(ic_c: float) -> str:
    """Converte um índice de calor (°C) na categoria de risco do NWS."""
    for limite, nome in FAIXAS_IC:
        if ic_c < limite:
            return nome
    return FAIXAS_IC[-1][1]


def nivel(categoria: str) -> int:
    """Nível numérico (0 a 4) de uma categoria, útil para ordenar e comparar."""
    nomes = [n for _, n in FAIXAS_IC]
    return nomes.index(categoria)
