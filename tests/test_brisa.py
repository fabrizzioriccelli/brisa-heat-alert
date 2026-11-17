"""Testes automatizados do Brisa (executar: python -m pytest -v)."""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from brisa import alertas, banco, config, dados, modelo, sensor  # noqa: E402
from brisa.indice_calor import (celsius_para_fahrenheit, classificar,  # noqa: E402
                                fahrenheit_para_celsius, indice_de_calor)


# ------------------------------------------------------------ índice de calor
@pytest.mark.parametrize("t_f, ur, esperado_f", [
    (90, 70, 106),   # valores da tabela oficial do NWS
    (86, 90, 105),
    (100, 40, 109),
    (80, 40, 80),
])
def test_indice_confere_com_tabela_nws(t_f, ur, esperado_f):
    ic_f = celsius_para_fahrenheit(indice_de_calor(fahrenheit_para_celsius(t_f), ur))
    assert abs(ic_f - esperado_f) <= 2.0  # a regressão de Rothfusz tem erro de ±1,3 °F


def test_ramo_simples_para_clima_ameno():
    assert indice_de_calor(20, 50) == pytest.approx(19.6, abs=0.5)


def test_ajuste_umidade_alta_aumenta_indice():
    assert indice_de_calor(28, 95) > indice_de_calor(28, 85)


@pytest.mark.parametrize("ic, cat", [(20, "Normal"), (26.7, "Cautela"), (32.19, "Cautela"),
                                     (32.2, "Cautela extrema"), (39.4, "Perigo"),
                                     (55, "Perigo extremo")])
def test_faixas(ic, cat):
    assert classificar(ic) == cat


@pytest.mark.parametrize("t, u", [(70, 50), (30, 120), (30, -1), (None, 50)])
def test_entradas_invalidas(t, u):
    with pytest.raises(ValueError):
        indice_de_calor(t, u)


# ------------------------------------------------------------ limpeza de dados
def test_limpeza_remove_duplicatas_e_valores_impossiveis():
    horas = pd.date_range("2025-01-01", periods=6, freq="h")
    df = pd.DataFrame({"data_hora": list(horas) + [horas[0]], "cidade": "x",
                       "temp": [25, 26, 99, 28, 29, 30, 25], "umidade": [60] * 7,
                       "vento": [5] * 7, "radiacao": [0] * 7, "sensacao_openmeteo": [25] * 7})
    limpo, rel = dados.limpar(df)
    assert rel["duplicatas_removidas"] == 1
    assert rel["valores_fora_da_faixa"] == 1
    assert len(limpo) == 6
    assert limpo["temp"].iloc[2] == pytest.approx(27.0)  # interpolado entre 26 e 28


def test_dataset_diario_sem_vazamento():
    d = pd.read_csv(config.ARQ_DIARIO)
    assert not any("tarde" in a and "ontem" not in a for a in modelo.ATRIBUTOS)
    assert set(modelo.ATRIBUTOS).issubset(d.columns)
    assert d["alvo_alerta"].isin([0, 1]).all()


# ------------------------------------------------------------ alertas
def test_regras_de_alerta():
    t0 = datetime(2025, 2, 17, 10, 0)
    assert not alertas.deve_alertar("Cautela", t0, None)
    assert alertas.deve_alertar("Cautela extrema", t0, None)
    ultimo = {"categoria": "Cautela extrema", "momento": t0}
    assert not alertas.deve_alertar("Cautela extrema", t0 + timedelta(minutes=30), ultimo)
    assert alertas.deve_alertar("Cautela extrema", t0 + timedelta(minutes=60), ultimo)
    assert alertas.deve_alertar("Perigo", t0 + timedelta(minutes=10), ultimo)


# ------------------------------------------------------------ sensores + banco
@pytest.fixture
def banco_temp(tmp_path):
    caminho = tmp_path / "teste.db"
    sensor.cadastrar_escola_demo(caminho)
    return caminho


def _linha(disp="brisa-sala-21", ts="2025-02-17T10:00:00", temp=34.0, umid=60.0):
    return json.dumps({"dispositivo": disp, "ts": ts, "temp": temp, "umid": umid})


@pytest.mark.parametrize("texto", [
    '{"dispositivo":"x","ts":"2025-02-17T10:0',
    '{"dispositivo":"x","temp":30,"umid":50}',
    _linha(temp=85), _linha(umid=101), _linha(ts=""),
])
def test_validacao_rejeita_linhas_ruins(texto):
    with pytest.raises(ValueError):
        sensor.validar_linha(texto)


def test_ingestao_grava_deduplica_e_alerta(banco_temp):
    linhas = [_linha(ts="2025-02-17T10:00:00"), _linha(ts="2025-02-17T10:00:00"),
              _linha(ts="2025-02-17T10:10:00"), _linha(disp="desconhecido"),
              _linha(ts="2025-02-17T10:20:00", temp=38, umid=60)]
    s = sensor.ingerir(linhas, caminho_banco=banco_temp)
    assert s["recebidas"] == 5
    assert s["gravadas"] == 3
    assert s["duplicadas"] == 1
    assert s["rejeitadas"] == 1
    assert s["alertas"] == 2  # 10:00 (Cautela extrema) e 10:20 (piorou para Perigo)
    with banco.conectar(banco_temp) as con:
        resumo = banco.resumo_ambientes(con)
        assert resumo[0]["leituras"] == 3


def test_banco_rejeita_valor_fisicamente_impossivel(banco_temp):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        with banco.conectar(banco_temp) as con:
            banco.inserir_leitura(con, 1, "2025-01-01T10:00", 99, 50, 0, "x", "manual")


# ------------------------------------------------------------ modelo
def test_previsao_retorna_campos_validos():
    d = pd.read_csv(config.ARQ_DIARIO)
    r = modelo.prever(d.iloc[-1].to_dict())
    assert r["faixa_prevista"] in modelo.CLASSES
    assert abs(sum(r["probabilidades"].values()) - 1) < 0.01
    assert 10 < r["pico_previsto"] < 55


def test_previsao_sem_atributos_falha():
    with pytest.raises(ValueError):
        modelo.prever({"temp_09h": 30})


def test_modelo_supera_linha_de_base():
    m = json.loads((config.DIR_MODELOS / "metricas.json").read_text(encoding="utf-8"))
    base = m["regressao"][0]["MAE"]
    assert min(r["MAE"] for r in m["regressao"][1:]) < base


# ------------------------------------------------------------ firmware (C++)
@pytest.mark.skipif(shutil.which("c++") is None, reason="compilador C++ indisponível")
def test_formula_do_esp32_igual_a_do_python(tmp_path):
    fonte = tmp_path / "t.cpp"
    fonte.write_text(
        '#include <cstdio>\n#include "brisa_ic.h"\nint main(){'
        'for(float t=20;t<=44;t+=1.5)for(float u=10;u<=100;u+=7.5)'
        'printf("%.2f %.2f %.4f %d\\n",t,u,brisa_indice_calor(t,u),brisa_nivel(brisa_indice_calor(t,u)));}')
    exe = tmp_path / "t"
    subprocess.run(["c++", "-std=c++17", "-I", str(RAIZ / "src" / "esp32"), str(fonte), "-o", str(exe)],
                   check=True)
    saida = subprocess.run([str(exe)], capture_output=True, text=True, check=True).stdout.split("\n")
    nomes = [n for _, n in config.FAIXAS_IC]
    n = 0
    for linha in filter(None, saida):
        t, u, ic_cpp, nivel = linha.split()
        ic_py = indice_de_calor(float(t), float(u))
        assert abs(float(ic_cpp) - ic_py) < 0.05
        if abs(ic_py - min(config.FAIXAS_IC, key=lambda f: abs(f[0] - ic_py))[0]) > 0.05:
            assert nomes[int(nivel)] == classificar(ic_py)
        n += 1
    assert n > 150
