"""Camada de sensores: simulação de leituras internas e ingestão do formato do ESP32.

O ESP32 (src/esp32) envia pela serial uma linha JSON por leitura, por exemplo:
  {"dispositivo":"brisa-sala-21","ts":"2025-02-17T10:20:00","temp":31.4,"umid":62.0}

Este módulo:
1. SIMULA esse fluxo para uma escola fictícia, partindo do clima externo REAL
   (Open-Meteo/ERA5) e somando um aquecimento interno HIPOTÉTICO por ambiente.
2. INGERE qualquer arquivo nesse formato (simulado ou capturado do ESP32/Wokwi),
   validando cada linha, recalculando o índice de calor e gerando alertas.
"""
import json
from datetime import datetime

import numpy as np
import pandas as pd

from . import alertas, banco, config
from .indice_calor import classificar, indice_de_calor

ESCOLA_DEMO = ("Escola Municipal Demonstração Brisa (fictícia)", "rio_de_janeiro")

# Hipóteses de aquecimento interno (°C): base + fator * radiação solar (kW/m²)
AMBIENTES_DEMO = [
    # nome, tipo, dispositivo, base, fator_radiacao, delta_umidade
    ("Sala 12 — térreo, ventilação cruzada", "sala", "brisa-sala-12", 0.8, 1.0, -2),
    ("Sala 21 — 2º andar, telhado de fibrocimento", "sala", "brisa-sala-21", 1.5, 3.5, -5),
    ("Quadra coberta", "quadra", "brisa-quadra", 0.5, 2.5, -3),
]


def escolher_semana_demo(df: pd.DataFrame, cidade="rio_de_janeiro", ano=2025):
    """Semana letiva (seg-sex) que contém o dia mais quente de fev-mar do ano."""
    g = df[(df["cidade"] == cidade) & (df["ano"] == ano) & df["mes"].isin([2, 3]) & df["horario_escolar"]]
    dia_pico = pd.Timestamp(g.loc[g["indice_calor"].idxmax(), "data"])
    segunda = dia_pico - pd.Timedelta(days=dia_pico.dayofweek)
    return [(segunda + pd.Timedelta(days=i)).date() for i in range(5)]


def simular_leituras(df: pd.DataFrame, dias, cidade="rio_de_janeiro", semente=config.SEMENTE,
                     incluir_falhas=True) -> list[str]:
    """Gera linhas JSON a cada 10 min (7h-17h) para cada ambiente da escola demo."""
    rng = np.random.default_rng(semente)
    ext = df[(df["cidade"] == cidade) & (df["data"].isin(dias))].set_index("data_hora").sort_index()
    ext = ext[["temp", "umidade", "radiacao"]].resample("10min").interpolate()
    ext = ext[(ext.index.hour >= config.HORA_INICIO_AULA) & (ext.index.hour < config.HORA_FIM_AULA)
              | ((ext.index.hour == config.HORA_FIM_AULA) & (ext.index.minute == 0))]
    linhas = []
    for nome, _, disp, base, fator, d_umid in AMBIENTES_DEMO:
        t_in = ext["temp"] + base + fator * ext["radiacao"] / 1000 + rng.normal(0, 0.3, len(ext))
        u_in = (ext["umidade"] + d_umid + rng.normal(0, 1.5, len(ext))).clip(15, 100)
        for ts, t, u in zip(ext.index, t_in, u_in):
            linhas.append(json.dumps({"dispositivo": disp, "ts": ts.isoformat(),
                                      "temp": round(float(t), 1), "umid": round(float(u), 1)}))
    linhas.sort(key=lambda s: json.loads(s)["ts"])
    if incluir_falhas:  # falhas de transmissão SIMULADAS para demonstrar a validação
        linhas.insert(10, '{"dispositivo":"brisa-sala-12","ts":"' + str(dias[0]) + 'T08:3')
        linhas.insert(25, json.dumps({"dispositivo": "brisa-sala-21",
                                      "ts": json.loads(linhas[24])["ts"],
                                      "temp": 85.0, "umid": 40.0}))
    return linhas


def salvar_simulacao(linhas, nome="leituras_esp32_simuladas.jsonl"):
    config.DIR_SIMULADOS.mkdir(parents=True, exist_ok=True)
    caminho = config.DIR_SIMULADOS / nome
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def validar_linha(texto: str) -> dict:
    """Converte e valida uma linha JSON. Levanta ValueError se for inválida."""
    try:
        d = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON malformado ({e.msg})") from e
    for campo in ("dispositivo", "ts", "temp", "umid"):
        if campo not in d:
            raise ValueError(f"campo ausente: {campo}")
    try:
        momento = datetime.fromisoformat(d["ts"])
        temp, umid = float(d["temp"]), float(d["umid"])
    except (TypeError, ValueError) as e:
        raise ValueError(f"valor inválido: {e}") from e
    if not -10 <= temp <= 60:
        raise ValueError(f"temperatura fora da faixa do sensor: {temp}")
    if not 0 <= umid <= 100:
        raise ValueError(f"umidade fora da faixa: {umid}")
    return {"dispositivo": d["dispositivo"], "momento": momento, "temp": temp, "umid": umid}


def ingerir(linhas, origem="simulado", caminho_banco=None) -> dict:
    """Grava leituras válidas no banco e dispara alertas em tempo real."""
    stats = {"recebidas": 0, "gravadas": 0, "duplicadas": 0, "rejeitadas": 0,
             "alertas": 0, "erros": []}
    ultimo_alerta = {}
    with banco.conectar(caminho_banco) as con:
        for n, texto in enumerate(linhas, start=1):
            texto = texto.strip()
            if not texto:
                continue
            stats["recebidas"] += 1
            try:
                d = validar_linha(texto)
                amb = banco.ambiente_por_dispositivo(con, d["dispositivo"])
                if amb is None:
                    raise ValueError(f"dispositivo não cadastrado: {d['dispositivo']}")
            except ValueError as e:
                stats["rejeitadas"] += 1
                stats["erros"].append(f"linha {n}: {e}")
                continue
            ic = indice_de_calor(d["temp"], d["umid"])
            cat = classificar(ic)
            ok = banco.inserir_leitura(con, amb["id"], d["momento"].isoformat(timespec="seconds"),
                                       d["temp"], d["umid"], ic, cat, origem)
            if not ok:
                stats["duplicadas"] += 1
                continue
            stats["gravadas"] += 1
            chave = (amb["id"], d["momento"].date())
            if alertas.deve_alertar(cat, d["momento"], ultimo_alerta.get(chave)):
                banco.inserir_alerta(con, amb["escola_id"], amb["id"],
                                     d["momento"].isoformat(timespec="seconds"), "tempo_real",
                                     cat, ic, alertas.montar_mensagem(amb["nome"], cat, ic))
                ultimo_alerta[chave] = {"categoria": cat, "momento": d["momento"]}
                stats["alertas"] += 1
    return stats


def cadastrar_escola_demo(caminho_banco=None) -> int:
    banco.criar_banco(caminho_banco)
    with banco.conectar(caminho_banco) as con:
        eid = banco.inserir_escola(con, ESCOLA_DEMO[0], ESCOLA_DEMO[1], simulada=True)
        for nome, tipo, disp, *_ in AMBIENTES_DEMO:
            banco.inserir_ambiente(con, eid, nome, tipo, disp)
    return eid
