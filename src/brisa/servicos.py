"""Serviços de alto nível usados pela linha de comando, pelo menu e pelo painel."""
import pandas as pd

from . import alertas, banco, config, dados, modelo, sensor
from .indice_calor import classificar


def carregar_diario() -> pd.DataFrame:
    if not config.ARQ_DIARIO.exists():
        raise FileNotFoundError("Dataset diário ausente. Rode 'python src/main.py preparar'.")
    d = pd.read_csv(config.ARQ_DIARIO, parse_dates=["data"])
    return d


def atributos_do_dia(diario: pd.DataFrame, cidade: str, data) -> dict:
    linha = diario[(diario["cidade"] == cidade) & (diario["data"] == pd.Timestamp(data))]
    if linha.empty:
        raise ValueError(f"Sem dados de manhã completos para {cidade} em {data} (ou não é dia útil).")
    return linha.iloc[0].to_dict()


def boletim_do_dia(cidade: str, data, diario=None, modelos=None) -> dict:
    """Boletim das 09h: previsão do pico da tarde + recomendações + valor observado."""
    diario = diario if diario is not None else carregar_diario()
    attrs = atributos_do_dia(diario, cidade, data)
    prev = modelo.prever(attrs, modelos)
    faixa = prev["faixa_prevista"]
    recs = list(alertas.recomendacoes(faixa))
    # Aviso preventivo: a probabilidade de "Perigo" passou do limiar calibrado,
    # mas a faixa mais provável é outra. Não muda a faixa; pede vigilância à tarde.
    aviso = bool(prev["alerta_perigo"] and faixa != "Perigo")
    if aviso:
        recs.append("Possibilidade de PERIGO à tarde: acompanhar os sensores das salas e "
                    "deixar o plano de remanejamento pronto.")
    return {
        "cidade": config.CIDADES[cidade][0],
        "data": str(pd.Timestamp(data).date()),
        "manha": {"temp_09h": attrs["temp_09h"], "umidade_09h": attrs["umidade_09h"],
                  "ic_09h": attrs["ic_09h"]},
        "pico_previsto": prev["pico_previsto"],
        "faixa_final": faixa,
        "aviso_perigo": aviso,
        "probabilidades": prev["probabilidades"],
        "recomendacoes": recs,
        "pico_observado": round(float(attrs["ic_max_tarde"]), 1),
        "faixa_observada": classificar(attrs["ic_max_tarde"]),
    }


def montar_demo(caminho_banco=None) -> dict:
    """Recria o banco da escola demo: simula a semana, ingere leituras e grava previsões."""
    destino = caminho_banco or config.CAMINHO_BANCO
    if destino.exists():
        destino.unlink()
    df = dados.carregar_horario()
    dias = sensor.escolher_semana_demo(df)
    escola_id = sensor.cadastrar_escola_demo(destino)
    linhas = sensor.simular_leituras(df, dias)
    arquivo = sensor.salvar_simulacao(linhas)
    stats = sensor.ingerir(linhas, origem="simulado", caminho_banco=destino)

    diario = carregar_diario()
    modelos = modelo.carregar_modelos()
    boletins = []
    with banco.conectar(destino) as con:
        for dia in dias:
            b = boletim_do_dia(sensor.ESCOLA_DEMO[1], dia, diario, modelos)
            boletins.append(b)
            banco.salvar_previsao(con, escola_id, b["data"], b["pico_previsto"], b["faixa_final"],
                                  b["probabilidades"].get("Perigo"), b["pico_observado"],
                                  b["faixa_observada"])
            if b["faixa_final"] in ("Cautela extrema", "Perigo", "Perigo extremo"):
                msg = (f"[PREVISÃO {b['faixa_final'].upper()}] Pico previsto de "
                       f"{b['pico_previsto']:.1f} °C entre 12h e 17h. {b['recomendacoes'][0]}")
                banco.inserir_alerta(con, escola_id, None, f"{b['data']}T09:00", "previsao",
                                     b["faixa_final"], b["pico_previsto"], msg)
    return {"dias": [str(d) for d in dias], "arquivo": str(arquivo.relative_to(config.RAIZ)),
            "ingestao": stats, "boletins": boletins}
