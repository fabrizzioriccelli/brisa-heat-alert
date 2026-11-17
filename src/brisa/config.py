"""Configurações centrais do Brisa (caminhos, cidades e limiares)."""
from pathlib import Path

# Raiz do projeto
RAIZ = Path(__file__).resolve().parents[2]

DIR_DADOS = RAIZ / "data"
DIR_BRUTOS = DIR_DADOS / "raw"
DIR_PROCESSADOS = DIR_DADOS / "processed"
DIR_SIMULADOS = DIR_DADOS / "simulated"
DIR_MODELOS = RAIZ / "models"
DIR_FIGURAS = RAIZ / "docs" / "img"
CAMINHO_BANCO = DIR_DADOS / "brisa.db"

ARQ_HORARIO = DIR_PROCESSADOS / "clima_horario_5_capitais.csv.gz"
ARQ_DIARIO = DIR_PROCESSADOS / "dataset_alerta_diario.csv"

# Cidades analisadas: (nome exibido, latitude, longitude, região)
CIDADES = {
    "sao_paulo": ("São Paulo (SP)", -23.55, -46.63, "Sudeste"),
    "rio_de_janeiro": ("Rio de Janeiro (RJ)", -22.91, -43.17, "Sudeste"),
    "cuiaba": ("Cuiabá (MT)", -15.60, -56.10, "Centro-Oeste"),
    "teresina": ("Teresina (PI)", -5.09, -42.80, "Nordeste"),
    "manaus": ("Manaus (AM)", -3.12, -60.02, "Norte"),
}

ANO_INICIO, ANO_FIM = 2020, 2025

# Período escolar considerado (dias úteis, 7h às 17h)
HORA_INICIO_AULA, HORA_FIM_AULA = 7, 17

# Janela da manhã usada como entrada do modelo e janela da tarde a prever
MANHA = (6, 9)    # 06h..09h (inclusive)
TARDE = (12, 17)  # 12h..17h (inclusive)

# Faixas do Índice de Calor do NWS/NOAA convertidas para °C
# (80 °F = 26,7 °C; 90 °F = 32,2 °C; 103 °F = 39,4 °C; 125 °F = 51,7 °C)
FAIXAS_IC = [
    (26.7, "Normal"),
    (32.2, "Cautela"),
    (39.4, "Cautela extrema"),
    (51.7, "Perigo"),
    (float("inf"), "Perigo extremo"),
]
LIMIAR_ALERTA = 32.2  # a partir de "Cautela extrema" o Brisa emite alerta

CORES_CATEGORIA = {
    "Normal": "#2E9E6B",
    "Cautela": "#E8C547",
    "Cautela extrema": "#F08A24",
    "Perigo": "#D63E2F",
    "Perigo extremo": "#7A1F3D",
}

SEMENTE = 42
