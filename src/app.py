"""Painel web do Brisa (Streamlit).

Executar a partir da pasta GLOBAL-SOLUTION-1:
    streamlit run src/app.py
"""
import sys
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brisa import alertas, banco, config, dados, modelo, servicos  # noqa: E402
from brisa.indice_calor import classificar, indice_de_calor  # noqa: E402

st.set_page_config(page_title="Brisa — calor seguro na escola", page_icon="🌬️", layout="wide")

st.markdown("""
<style>
.brisa-badge {display:inline-block;padding:4px 12px;border-radius:999px;color:#fff;font-weight:600}
.brisa-card {border:1px solid rgba(128,128,128,.25);border-radius:12px;padding:14px 16px}
.brisa-card h4 {margin:0 0 4px 0;font-size:.85rem;opacity:.7;font-weight:500}
.brisa-card p {margin:0;font-size:1.6rem;font-weight:700}
</style>""", unsafe_allow_html=True)


def badge(cat):
    cor = config.CORES_CATEGORIA.get(cat, "#666")
    texto = "#222" if cat == "Cautela" else "#fff"
    return f'<span class="brisa-badge" style="background:{cor};color:{texto}">{cat}</span>'


def card(col, titulo, valor):
    col.markdown(f'<div class="brisa-card"><h4>{titulo}</h4><p>{valor}</p></div>',
                 unsafe_allow_html=True)


@st.cache_data
def carregar():
    return dados.carregar_horario(), servicos.carregar_diario()


@st.cache_resource
def modelos():
    return modelo.carregar_modelos()


try:
    horario, diario = carregar()
    mods = modelos()
except FileNotFoundError as e:
    st.error(f"{e}\n\nExecute antes: `python src/main.py tudo`")
    st.stop()

st.title("🌬️ Brisa")
st.caption("Calor seguro na escola: previsão com IA às 09h + sensores nas salas + recomendações para a coordenação.")

aba1, aba2, aba3, aba4 = st.tabs(["☀️ Boletim das 09h", "🏫 Salas em tempo real",
                                  "📊 Panorama 2020-2025", "🧮 Calculadora"])

# ------------------------------------------------------------------ Boletim
with aba1:
    c1, c2 = st.columns([1, 1])
    cidade = c1.selectbox("Cidade da escola", list(config.CIDADES),
                          format_func=lambda c: config.CIDADES[c][0], index=1)
    dia = c2.date_input("Dia letivo", value=date(2025, 2, 18), min_value=date(2020, 1, 2),
                        max_value=date(2025, 12, 31), format="DD/MM/YYYY")
    try:
        b = servicos.boletim_do_dia(cidade, dia, diario, mods)
    except ValueError as e:
        st.warning(f"{e} Escolha um dia de segunda a sexta.")
        st.stop()

    k1, k2, k3, k4 = st.columns(4)
    card(k1, "Temperatura às 09h", f"{b['manha']['temp_09h']:.1f} °C")
    card(k2, "Umidade às 09h", f"{b['manha']['umidade_09h']:.0f} %")
    card(k3, "Índice de calor às 09h", f"{b['manha']['ic_09h']:.1f} °C")
    card(k4, "Pico previsto 12h-17h", f"{b['pico_previsto']:.1f} °C")

    st.markdown(f"### Faixa prevista para a tarde: {badge(b['faixa_final'])}", unsafe_allow_html=True)
    if b["aviso_perigo"]:
        st.warning("Aviso preventivo: a probabilidade de PERIGO passou do limiar de segurança do modelo.")

    e, d = st.columns([1.1, 1])
    with e:
        st.markdown("**O que fazer hoje**")
        for r in b["recomendacoes"]:
            st.markdown(f"- {r}")
        st.markdown("**Probabilidade de cada faixa (Random Forest)**")
        probs = pd.DataFrame({"faixa": list(b["probabilidades"]),
                              "prob": list(b["probabilidades"].values())})
        st.altair_chart(alt.Chart(probs).mark_bar().encode(
            x=alt.X("prob:Q", axis=alt.Axis(format="%"), title=None),
            y=alt.Y("faixa:N", sort=modelo.CLASSES, title=None),
            color=alt.Color("faixa:N", scale=alt.Scale(domain=list(config.CORES_CATEGORIA),
                                                        range=list(config.CORES_CATEGORIA.values())),
                            legend=None)).properties(height=150), width="stretch")
    with d:
        st.markdown("**Curva real do dia (dado ERA5) — verificação do boletim**")
        g = horario[(horario["cidade"] == cidade) & (horario["data"] == dia)]
        base = alt.Chart(g).encode(x=alt.X("hora:Q", title="hora"))
        linha = base.mark_line(point=True, color="#F08A24").encode(
            y=alt.Y("indice_calor:Q", title="índice de calor (°C)", scale=alt.Scale(zero=False)),
            tooltip=["hora", "temp", "umidade", "indice_calor", "categoria"])
        limiar = alt.Chart(pd.DataFrame({"y": [config.LIMIAR_ALERTA]})).mark_rule(
            color="#D63E2F", strokeDash=[4, 4]).encode(y="y:Q")
        st.altair_chart(linha + limiar, width="stretch")
        st.caption(f"Pico observado entre 12h e 17h: **{b['pico_observado']:.1f} °C** "
                   f"({b['faixa_observada']}). A linha tracejada marca 32,2 °C.")

# ------------------------------------------------------------------ Salas
with aba2:
    st.info("Ambientes e leituras SIMULADOS: escola fictícia no Rio de Janeiro, clima externo real "
            "(ERA5) + aquecimento interno hipotético por ambiente, no mesmo formato JSON do ESP32.")
    if not config.CAMINHO_BANCO.exists():
        st.error("Banco não encontrado. Rode `python src/main.py demo`.")
    else:
        with banco.conectar() as con:
            datas = banco.datas_disponiveis(con)
            sel = st.selectbox("Dia", datas, index=min(1, len(datas) - 1))
            leit = pd.DataFrame([dict(r) for r in banco.leituras_do_dia(con, sel)])
            resumo = pd.DataFrame([dict(r) for r in banco.resumo_ambientes(con, sel)])
            alts = pd.DataFrame([dict(r) for r in banco.alertas_recentes(con, 200)])
        leit["data_hora"] = pd.to_datetime(leit["data_hora"])
        st.altair_chart(alt.Chart(leit).mark_line().encode(
            x=alt.X("data_hora:T", title="horário", axis=alt.Axis(format="%H:%M")),
            y=alt.Y("indice_calor:Q", title="índice de calor (°C)", scale=alt.Scale(zero=False)),
            color=alt.Color("ambiente:N", legend=alt.Legend(orient="bottom", columns=1)),
            tooltip=["ambiente", "data_hora", "temperatura", "umidade", "indice_calor", "categoria"],
        ).properties(height=320) + alt.Chart(pd.DataFrame({"y": [config.LIMIAR_ALERTA]}))
            .mark_rule(color="#D63E2F", strokeDash=[4, 4]).encode(y="y:Q"),
            width="stretch")
        st.markdown("**Resumo por ambiente** (minutos em alerta = leituras de 10 min com IC ≥ 32,2 °C)")
        st.dataframe(resumo, hide_index=True, width="stretch")
        mais_fresco = resumo.sort_values("ic_medio").iloc[0]["ambiente"]
        st.success(f"Ambiente mais fresco do dia para remanejar turmas: **{mais_fresco}**")
        st.markdown("**Alertas do dia**")
        if not alts.empty:
            st.dataframe(alts[alts["data_hora"].str.startswith(sel)], hide_index=True,
                         width="stretch")

# ------------------------------------------------------------------ Panorama
with aba3:
    st.markdown("Dados reais horários (Open-Meteo/ERA5), 2020-2025, dias úteis das 7h às 17h.")
    figs = [("fig_horas_alerta_ano.png", "Horas de aula por ano com índice de calor ≥ 32,2 °C"),
            ("fig_categorias_cidades.png", "Faixas de risco nas horas de aula"),
            ("fig_mapa_mes_hora.png", "Quando o risco se concentra (mês x hora)"),
            ("fig_matriz_confusao.png", "Desempenho do classificador no teste 2024-2025")]
    c = st.columns(2)
    for i, (arq, leg) in enumerate(figs):
        caminho = config.DIR_FIGURAS / arq
        if caminho.exists():
            c[i % 2].image(str(caminho), caption=leg, width="stretch")

# ------------------------------------------------------------------ Calculadora
with aba4:
    a, b2 = st.columns(2)
    t = a.slider("Temperatura (°C)", 15.0, 45.0, 32.0, 0.5)
    u = b2.slider("Umidade relativa (%)", 10, 100, 60)
    ic = indice_de_calor(t, u)
    cat = classificar(ic)
    st.markdown(f"## {ic:.1f} °C {badge(cat)}", unsafe_allow_html=True)
    for r in alertas.recomendacoes(cat):
        st.markdown(f"- {r}")

st.divider()
st.caption("Protótipo acadêmico (FIAP Global Solution 2026.2). Faixas do índice de calor do NWS/NOAA. "
           "As recomendações não substituem orientação de profissionais de saúde nem protocolos oficiais.")
