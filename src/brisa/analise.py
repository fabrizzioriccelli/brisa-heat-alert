"""Análise exploratória e estatística da exposição ao calor em horário escolar."""
import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from . import config

ORDEM_CAT = [n for _, n in config.FAIXAS_IC]
sns.set_theme(style="whitegrid", font_scale=0.95)


def _nome(c):
    return config.CIDADES[c][0]


def _salvar(nome):
    config.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(config.DIR_FIGURAS / nome, dpi=150)
    plt.close()


def estatisticas_descritivas(df: pd.DataFrame) -> pd.DataFrame:
    esc = df[df["horario_escolar"]]
    t = esc.groupby("cidade")["indice_calor"].agg(
        media="mean", desvio_padrao="std", mediana="median",
        p95=lambda s: s.quantile(0.95), maximo="max").round(1)
    t["horas_escolares"] = esc.groupby("cidade").size()
    t["pct_horas_alerta"] = (esc.groupby("cidade")["alerta"].mean() * 100).round(1)
    t.index = [_nome(c) for c in t.index]
    return t.sort_values("media", ascending=False)


def distribuicao_categorias(df: pd.DataFrame) -> pd.DataFrame:
    esc = df[df["horario_escolar"]]
    t = pd.crosstab(esc["cidade"], esc["categoria"], normalize="index") * 100
    t = t.reindex(columns=[c for c in ORDEM_CAT if c in t.columns]).round(1)
    t.index = [_nome(c) for c in t.index]
    return t


def horas_alerta_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    esc = df[df["horario_escolar"]]
    t = esc.groupby(["cidade", "ano"])["alerta"].sum().unstack()
    t.index = [_nome(c) for c in t.index]
    return t


def dias_criticos(df: pd.DataFrame, horas_minimas: int = 4) -> pd.DataFrame:
    """Dias letivos com pelo menos N horas de aula em 'Cautela extrema' ou pior."""
    esc = df[df["horario_escolar"]]
    por_dia = esc.groupby(["cidade", "ano", "data"])["alerta"].sum().reset_index()
    por_dia["critico"] = por_dia["alerta"] >= horas_minimas
    t = por_dia.groupby(["cidade", "ano"])["critico"].sum().unstack()
    t.index = [_nome(c) for c in t.index]
    return t


def comparar_periodos(df: pd.DataFrame) -> pd.DataFrame:
    """Teste t de Welch: pico diário do IC em 2020-2022 vs 2023-2025 (dias úteis)."""
    esc = df[df["horario_escolar"]]
    pico = esc.groupby(["cidade", "ano", "data"])["indice_calor"].max().reset_index()
    linhas = []
    for c, g in pico.groupby("cidade"):
        a = g[g["ano"] <= 2022]["indice_calor"]
        b = g[g["ano"] >= 2023]["indice_calor"]
        t, p = stats.ttest_ind(b, a, equal_var=False)
        linhas.append({"cidade": _nome(c), "media_2020_2022": round(a.mean(), 2),
                       "media_2023_2025": round(b.mean(), 2),
                       "diferenca": round(b.mean() - a.mean(), 2),
                       "t": round(t, 2), "p_valor": float(f"{p:.2g}")})
    return pd.DataFrame(linhas).set_index("cidade")


def validar_indice(df: pd.DataFrame) -> dict:
    """Compara o IC calculado com a sensação térmica independente da Open-Meteo."""
    r, _ = stats.pearsonr(df["indice_calor"], df["sensacao_openmeteo"])
    return {"pearson_ic_vs_sensacao_openmeteo": round(float(r), 3),
            "diferenca_media_C": round(float((df["indice_calor"] - df["sensacao_openmeteo"]).mean()), 2)}


# ---------------------------------------------------------------- figuras
def fig_horas_alerta(t: pd.DataFrame):
    plt.figure(figsize=(8, 4.4))
    paleta = ["#7A1F3D", "#D63E2F", "#F08A24", "#2E7DA6", "#2E9E6B"]
    for (cidade, linha), cor in zip(t.sort_values(2025, ascending=False).iterrows(), paleta):
        plt.plot(linha.index, linha.values, marker="o", lw=2, label=cidade, color=cor)
    plt.title("Horas de aula com índice de calor ≥ 32,2 °C (Cautela extrema ou pior)")
    plt.ylabel("horas por ano (dias úteis, 7h-17h)"); plt.xlabel("ano")
    plt.legend(fontsize=8, ncol=2); _salvar("fig_horas_alerta_ano.png")


def fig_boxplot(df: pd.DataFrame):
    esc = df[df["horario_escolar"]].copy()
    esc["Cidade"] = esc["cidade"].map(_nome)
    ordem = esc.groupby("Cidade")["indice_calor"].median().sort_values(ascending=False).index
    plt.figure(figsize=(8, 4.4))
    sns.boxplot(data=esc, x="Cidade", y="indice_calor", order=ordem, color="#F7B267",
                fliersize=1, linewidth=0.8)
    for lim, nome in config.FAIXAS_IC[:3]:
        plt.axhline(lim, ls="--", lw=0.8, color=config.CORES_CATEGORIA[nome])
        plt.text(4.55, lim + 0.3, f"{lim:.1f} °C", fontsize=7, ha="right")
    plt.ylabel("Índice de calor (°C)"); plt.xlabel("")
    plt.title("Distribuição do índice de calor em horário escolar (2020-2025)")
    _salvar("fig_boxplot_cidades.png")


def fig_mapa_mes_hora(df: pd.DataFrame, cidades=("rio_de_janeiro", "cuiaba")):
    fig, eixos = plt.subplots(1, len(cidades), figsize=(10, 4), sharey=True)
    for ax, c in zip(eixos, cidades):
        g = df[(df["cidade"] == c) & df["hora"].between(6, 19)]
        piv = g.pivot_table(index="hora", columns="mes", values="indice_calor", aggfunc="mean")
        sns.heatmap(piv, ax=ax, cmap="YlOrRd", vmin=15, vmax=36, cbar=ax is eixos[-1],
                    cbar_kws={"label": "IC médio (°C)"})
        ax.set_title(_nome(c)); ax.set_xlabel("mês"); ax.set_ylabel("hora do dia")
    fig.suptitle("Índice de calor médio por mês e hora — quando o risco se concentra")
    _salvar("fig_mapa_mes_hora.png")


def fig_correlacao(df: pd.DataFrame):
    cols = {"temp": "Temperatura", "umidade": "Umidade", "vento": "Vento",
            "radiacao": "Radiação", "indice_calor": "Índice de calor"}
    corr = df[list(cols)].rename(columns=cols).corr()
    plt.figure(figsize=(5.6, 4.6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1)
    plt.title("Correlação de Pearson entre variáveis (base horária)")
    _salvar("fig_correlacao.png")


def fig_categorias(t: pd.DataFrame):
    ax = t.plot.barh(stacked=True, figsize=(8, 3.8),
                     color=[config.CORES_CATEGORIA[c] for c in t.columns], width=0.7)
    ax.set_xlabel("% das horas de aula"); ax.set_ylabel("")
    ax.set_title("Faixa de risco do índice de calor nas horas de aula (2020-2025)")
    ax.legend(fontsize=8, bbox_to_anchor=(1.0, 1.0), loc="upper left")
    _salvar("fig_categorias_cidades.png")


def executar(df: pd.DataFrame) -> dict:
    desc = estatisticas_descritivas(df)
    cat = distribuicao_categorias(df)
    horas = horas_alerta_por_ano(df)
    criticos = dias_criticos(df)
    periodos = comparar_periodos(df)
    valid = validar_indice(df)

    fig_horas_alerta(horas); fig_boxplot(df); fig_mapa_mes_hora(df)
    fig_correlacao(df); fig_categorias(cat)

    saida = {
        "descritivas": desc.reset_index(names="cidade").to_dict("records"),
        "categorias_pct": cat.reset_index(names="cidade").to_dict("records"),
        "horas_alerta_ano": horas.reset_index(names="cidade").to_dict("records"),
        "dias_criticos_ano": criticos.reset_index(names="cidade").to_dict("records"),
        "comparacao_periodos": periodos.reset_index().to_dict("records"),
        "validacao_indice": valid,
    }
    config.DIR_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    with open(config.DIR_PROCESSADOS / "resultados_analise.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return {"descritivas": desc, "categorias": cat, "horas": horas, "criticos": criticos,
            "periodos": periodos, "validacao": valid}
