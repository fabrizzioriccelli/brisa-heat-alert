"""Coleta, leitura, limpeza e preparação dos dados meteorológicos reais."""
import time
import urllib.request

import numpy as np
import pandas as pd

from . import config
from .indice_calor import classificar, indice_de_calor

URL_ARQUIVO = (
    "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
    "&start_date={ini}-01-01&end_date={fim}-12-31"
    "&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "wind_speed_10m,shortwave_radiation"
    "&timezone=America%2FSao_Paulo&format=csv"
)

COLUNAS = {
    "time": "data_hora",
    "temperature_2m (°C)": "temp",
    "relative_humidity_2m (%)": "umidade",
    "apparent_temperature (°C)": "sensacao_openmeteo",
    "wind_speed_10m (km/h)": "vento",
    "shortwave_radiation (W/m²)": "radiacao",
}


def caminho_bruto(cidade: str):
    return config.DIR_BRUTOS / f"openmeteo_{cidade}_{config.ANO_INICIO}_{config.ANO_FIM}.csv"


def baixar_dados(forcar: bool = False) -> None:
    """Baixa o histórico horário (ERA5 via Open-Meteo) de cada cidade."""
    config.DIR_BRUTOS.mkdir(parents=True, exist_ok=True)
    for chave, (nome, lat, lon, _) in config.CIDADES.items():
        destino = caminho_bruto(chave)
        if destino.exists() and not forcar:
            print(f"  [ok] {nome}: arquivo já existe")
            continue
        url = URL_ARQUIVO.format(lat=lat, lon=lon, ini=config.ANO_INICIO, fim=config.ANO_FIM)
        print(f"  [baixando] {nome} ...")
        urllib.request.urlretrieve(url, destino)
        time.sleep(1)  # respeita o limite de requisições da API


def ler_cidade(chave: str) -> pd.DataFrame:
    """Lê o CSV da Open-Meteo (3 linhas de metadados + cabeçalho)."""
    arquivo = caminho_bruto(chave)
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}. Rode 'python src/main.py baixar'.")
    df = pd.read_csv(arquivo, skiprows=3).rename(columns=COLUNAS)
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df["cidade"] = chave
    return df


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove duplicatas e valores impossíveis; interpola lacunas curtas.

    Retorna o DataFrame limpo e um relatório com o que foi tratado.
    """
    rel = {"linhas_entrada": len(df)}
    df = df.drop_duplicates(subset=["cidade", "data_hora"]).copy()
    rel["duplicatas_removidas"] = rel["linhas_entrada"] - len(df)

    regras = {"temp": (-10, 50), "umidade": (0, 100), "vento": (0, 200), "radiacao": (0, 1500)}
    invalidos = 0
    for col, (mn, mx) in regras.items():
        fora = ~df[col].between(mn, mx) & df[col].notna()
        invalidos += int(fora.sum())
        df.loc[fora, col] = np.nan
    rel["valores_fora_da_faixa"] = invalidos
    rel["nulos_antes"] = int(df[list(regras)].isna().sum().sum())

    # Interpolação linear limitada a 3 horas consecutivas, por cidade
    df = df.sort_values(["cidade", "data_hora"])
    df[list(regras)] = df.groupby("cidade")[list(regras)].transform(
        lambda s: s.interpolate(limit=3, limit_direction="both"))
    df = df.dropna(subset=["temp", "umidade"])
    rel["nulos_depois"] = int(df[list(regras)].isna().sum().sum())
    rel["linhas_saida"] = len(df)
    return df, rel


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula o índice de calor, a categoria e marcadores de calendário."""
    df = df.copy()
    df["indice_calor"] = [indice_de_calor(t, u) for t, u in zip(df["temp"], df["umidade"])]
    df["categoria"] = df["indice_calor"].apply(classificar)
    df["data"] = df["data_hora"].dt.date
    df["ano"] = df["data_hora"].dt.year
    df["mes"] = df["data_hora"].dt.month
    df["hora"] = df["data_hora"].dt.hour
    df["dia_util"] = df["data_hora"].dt.dayofweek < 5
    df["horario_escolar"] = df["dia_util"] & df["hora"].between(
        config.HORA_INICIO_AULA, config.HORA_FIM_AULA)
    df["alerta"] = df["indice_calor"] >= config.LIMIAR_ALERTA
    return df


def preparar() -> dict:
    """Pipeline completo: lê as 5 cidades, limpa, enriquece e salva."""
    partes = [ler_cidade(c) for c in config.CIDADES]
    bruto = pd.concat(partes, ignore_index=True)
    limpo, relatorio = limpar(bruto)
    final = enriquecer(limpo)
    config.DIR_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    final.to_csv(config.ARQ_HORARIO, index=False, compression="gzip")
    relatorio["arquivo"] = str(config.ARQ_HORARIO.relative_to(config.RAIZ))
    return relatorio


def carregar_horario() -> pd.DataFrame:
    if not config.ARQ_HORARIO.exists():
        raise FileNotFoundError("Base processada ausente. Rode 'python src/main.py preparar'.")
    df = pd.read_csv(config.ARQ_HORARIO, parse_dates=["data_hora"])
    df["data"] = pd.to_datetime(df["data"]).dt.date
    return df


def montar_dataset_diario(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por cidade e dia útil: atributos da manhã + alvo da tarde.

    Só usa informação disponível até as 09h do próprio dia (e do dia anterior),
    evitando vazamento de dados para o modelo.
    """
    m0, m1 = config.MANHA
    t0, t1 = config.TARDE
    linhas = []
    for (cidade, data), g in df.groupby(["cidade", "data"]):
        g = g.set_index("hora")
        if not set(range(m0, m1 + 1)).issubset(g.index) or not set(range(t0, t1 + 1)).issubset(g.index):
            continue
        manha = g.loc[m0:m1]
        tarde = g.loc[t0:t1]
        linhas.append({
            "cidade": cidade,
            "data": pd.Timestamp(data),
            "dia_util": bool(g["dia_util"].iloc[0]),
            "temp_09h": g.at[m1, "temp"],
            "umidade_09h": g.at[m1, "umidade"],
            "ic_09h": g.at[m1, "indice_calor"],
            "temp_06h": g.at[m0, "temp"],
            "aquecimento_manha": g.at[m1, "temp"] - g.at[m0, "temp"],
            "radiacao_manha": manha["radiacao"].sum(),
            "vento_09h": g.at[m1, "vento"],
            "ic_max_tarde": tarde["indice_calor"].max(),
            "temp_max_tarde": tarde["temp"].max(),
        })
    d = pd.DataFrame(linhas).sort_values(["cidade", "data"]).reset_index(drop=True)
    # Atributos do dia anterior (persistência do calor)
    d["ic_max_tarde_ontem"] = d.groupby("cidade")["ic_max_tarde"].shift(1)
    d["mes_sen"] = np.sin(2 * np.pi * d["data"].dt.month / 12)
    d["mes_cos"] = np.cos(2 * np.pi * d["data"].dt.month / 12)
    d["alvo_alerta"] = (d["ic_max_tarde"] >= config.LIMIAR_ALERTA).astype(int)
    d = d.dropna().reset_index(drop=True)
    d = d[d["dia_util"]].drop(columns="dia_util").reset_index(drop=True)
    d.to_csv(config.ARQ_DIARIO, index=False)
    return d
