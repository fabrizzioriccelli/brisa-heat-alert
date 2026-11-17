"""Motor de alertas e recomendações para a rotina escolar.

As recomendações são sugestões operacionais de um protótipo acadêmico, baseadas
nas faixas do índice de calor do NWS/NOAA. Não substituem orientação de
profissionais de saúde nem protocolos oficiais da rede de ensino.
"""
from datetime import datetime, timedelta

from .indice_calor import nivel

RECOMENDACOES = {
    "Normal": [
        "Rotina normal.",
        "Manter garrafas de água acessíveis às turmas.",
    ],
    "Cautela": [
        "Lembrar as turmas de beber água em todos os intervalos.",
        "Preferir sombra para atividades ao ar livre perto do horário de pico.",
    ],
    "Cautela extrema": [
        "Pausas para hidratação a cada 30 minutos.",
        "Levar a educação física ao ar livre para um local sombreado e ventilado, ou para outro horário.",
        "Abrir janelas e portas para ventilação cruzada; desligar equipamentos que aquecem a sala.",
        "Equipe atenta a sinais de mal-estar (tontura, dor de cabeça, cansaço fora do comum).",
    ],
    "Perigo": [
        "Suspender atividades físicas intensas.",
        "Remanejar turmas das salas mais quentes para os ambientes mais frescos indicados pelo Brisa.",
        "Avisar a coordenação e as famílias; acionar o protocolo de saúde da rede de ensino.",
        "Reforçar a hidratação e oferecer pausas em local fresco.",
    ],
    "Perigo extremo": [
        "Avaliar com a gestão escolar e a Defesa Civil a suspensão das atividades presenciais.",
        "Seguir imediatamente o protocolo de emergência da rede.",
    ],
}

INTERVALO_REPETICAO = timedelta(minutes=60)


def recomendacoes(categoria: str) -> list[str]:
    return RECOMENDACOES.get(categoria, RECOMENDACOES["Normal"])


def deve_alertar(categoria: str, momento: datetime, ultimo: dict | None) -> bool:
    """Decide se uma leitura gera um alerta novo, evitando excesso de notificações.

    Regras:
    1. Só alerta a partir de "Cautela extrema".
    2. Alerta sempre que a categoria piora em relação ao último alerta.
    3. Repete a mesma categoria apenas depois de 60 minutos.
    """
    if nivel(categoria) < nivel("Cautela extrema"):
        return False
    if ultimo is None:
        return True
    if nivel(categoria) > nivel(ultimo["categoria"]):
        return True
    return momento - ultimo["momento"] >= INTERVALO_REPETICAO


def montar_mensagem(ambiente: str, categoria: str, ic: float) -> str:
    acao = recomendacoes(categoria)[0]
    return f"[{categoria.upper()}] {ambiente}: índice de calor {ic:.1f} °C. {acao}"
