"""Gera o relatório de entrega (HTML + PDF) a partir dos resultados reais do projeto.

Uso (na pasta GLOBAL-SOLUTION-1, depois de `python src/main.py tudo`):
    python docs/gerar_relatorio.py

Os nomes do grupo, a turma e os links ficam em docs/equipe.json: edite e rode de novo.
O PDF é impresso com o Google Chrome em modo headless.
"""
import ast
import html
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
RAIZ = DOCS.parent
SRC = RAIZ / "src"

equipe = json.loads((DOCS / "equipe.json").read_text(encoding="utf-8"))
an = json.loads((RAIZ / "data/processed/resultados_analise.json").read_text(encoding="utf-8"))
met = json.loads((RAIZ / "models/metricas.json").read_text(encoding="utf-8"))
testes = (DOCS / "evidencia_testes.txt").read_text(encoding="utf-8")
pipeline = (DOCS / "evidencia_execucao_pipeline.txt").read_text(encoding="utf-8")


# ------------------------------------------------------------------ utilidades
def e(x):
    return html.escape(str(x))


def funcao(arquivo, nome):
    """Código-fonte real de uma função, extraído do arquivo (fica sempre sincronizado)."""
    texto = (SRC / arquivo).read_text(encoding="utf-8")
    for no in ast.walk(ast.parse(texto)):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return ast.get_source_segment(texto, no)
    raise KeyError(nome)


def trecho(arquivo, inicio, fim):
    texto = (SRC / arquivo).read_text(encoding="utf-8")
    a = texto.index(inicio)
    b = texto.index(fim, a) + len(fim)
    return texto[a:b]


def codigo(src, legenda, lang="python"):
    return (f'<figure class="code"><figcaption>{legenda}</figcaption>'
            f'<pre><code class="{lang}">{e(src)}</code></pre></figure>')


def fig(arq, legenda, largura="100%"):
    return (f'<figure class="img"><img src="img/{arq}" style="width:{largura}">'
            f'<figcaption>{legenda}</figcaption></figure>')


def tabela(linhas, colunas, cabecalho=None, legenda="", num=None):
    cab = cabecalho or colunas
    h = "".join(f"<th>{e(c)}</th>" for c in cab)
    corpo = ""
    for li in linhas:
        corpo += "<tr>" + "".join(
            f"<td>{e(fmt(li.get(c, '')))}</td>" for c in colunas) + "</tr>"
    leg = f"<caption>{legenda}</caption>" if legenda else ""
    return f'<table>{leg}<thead><tr>{h}</tr></thead><tbody>{corpo}</tbody></table>'


def fmt(v):
    if isinstance(v, float):
        s = f"{v:,.3f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(v, int) and abs(v) >= 1000:
        return f"{v:,}".replace(",", ".")
    return v


def pct(v):
    return f"{v * 100:.1f}%".replace(".", ",")


# ------------------------------------------------------------------ dados para o texto
desc = {d["cidade"]: d for d in an["descritivas"]}
reg = met["regressao"]; clf = met["classificacao"]; ap = met["alerta_perigo"]
rf_reg = next(r for r in reg if r["modelo"] == "Random Forest")
base_reg = reg[0]
rf_clf = next(r for r in clf if r["modelo"] == "Random Forest")
base_clf = clf[0]
rep = met["relatorio_melhor_classificador"]

con = sqlite3.connect(RAIZ / "data/brisa.db"); con.row_factory = sqlite3.Row
prev_demo = [dict(r) for r in con.execute("SELECT data, pico_previsto, faixa_prevista, prob_perigo, "
                                          "pico_observado, faixa_observada FROM previsoes ORDER BY data")]
resumo_demo = [dict(r) for r in con.execute("""
    SELECT a.nome AS ambiente, ROUND(AVG(l.indice_calor),1) AS ic_medio, ROUND(MAX(l.indice_calor),1) AS ic_maximo,
           SUM(CASE WHEN l.indice_calor >= 32.2 THEN 10 ELSE 0 END) AS minutos_em_alerta,
           SUM(CASE WHEN l.indice_calor >= 39.4 THEN 10 ELSE 0 END) AS minutos_em_perigo
    FROM leituras l JOIN ambientes a ON a.id = l.ambiente_id GROUP BY a.id ORDER BY ic_medio DESC""")]
n_leituras = con.execute("SELECT COUNT(*) FROM leituras").fetchone()[0]
n_alertas = dict(con.execute("SELECT tipo, COUNT(*) FROM alertas GROUP BY tipo").fetchall())
con.close()
acertos_demo = sum(p["faixa_prevista"] == p["faixa_observada"] for p in prev_demo)
n_testes = testes.count(" PASSED")

linhas_testes = [l.split("::")[1].replace(" PASSED", "").split("[")[0].strip()
                 for l in testes.splitlines() if " PASSED" in l]
testes_unicos = list(dict.fromkeys(linhas_testes))

# ------------------------------------------------------------------ diagrama de arquitetura (SVG)
ARQ_SVG = """
<svg viewBox="0 0 900 378" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial" font-size="12">
 <defs><marker id="s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
 <path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
 <rect x="10" y="20" width="190" height="150" rx="10" fill="#FFF4E6" stroke="#F08A24"/>
 <text x="105" y="42" text-anchor="middle" font-weight="bold">1. Fontes de dados</text>
 <text x="22" y="66">• Open-Meteo / ERA5 (REAL)</text><text x="30" y="82">horário, 2020-2025, 5 capitais</text>
 <text x="22" y="108">• ESP32 + DHT22 nas salas</text><text x="30" y="124">JSON pela serial</text>
 <text x="22" y="150">• Leituras SIMULADAS (demo)</text>
 <rect x="250" y="20" width="200" height="150" rx="10" fill="#E8F4FA" stroke="#2E7DA6"/>
 <text x="350" y="42" text-anchor="middle" font-weight="bold">2. Ingestão e tratamento</text>
 <text x="262" y="66">• dados.py: leitura, limpeza,</text><text x="270" y="82">interpolação, horário escolar</text>
 <text x="262" y="108">• sensor.py: validação linha a</text><text x="270" y="124">linha, rejeição de erros</text>
 <text x="262" y="150">• indice_calor.py (NWS/NOAA)</text>
 <rect x="500" y="20" width="180" height="150" rx="10" fill="#EEF7F0" stroke="#2E9E6B"/>
 <text x="590" y="42" text-anchor="middle" font-weight="bold">3. Inteligência</text>
 <text x="512" y="66">• analise.py: estatística,</text><text x="520" y="82">teste t, gráficos</text>
 <text x="512" y="108">• modelo.py: Random Forest</text><text x="520" y="124">regressão + classificação</text>
 <text x="512" y="150">• alertas.py: regras</text>
 <rect x="730" y="20" width="160" height="150" rx="10" fill="#F6EEF3" stroke="#7A1F3D"/>
 <text x="810" y="42" text-anchor="middle" font-weight="bold">4. Persistência</text>
 <text x="742" y="66">SQLite (banco.py)</text><text x="742" y="90">escolas · ambientes</text>
 <text x="742" y="108">leituras · alertas</text><text x="742" y="126">previsoes</text>
 <text x="742" y="150">CHECK + UNIQUE + FK</text>
 <line x1="200" y1="95" x2="248" y2="95" stroke="#555" marker-end="url(#s)"/>
 <line x1="450" y1="95" x2="498" y2="95" stroke="#555" marker-end="url(#s)"/>
 <line x1="680" y1="95" x2="728" y2="95" stroke="#555" marker-end="url(#s)"/>
 <rect x="250" y="230" width="640" height="120" rx="10" fill="#FAFAFA" stroke="#999"/>
 <text x="570" y="252" text-anchor="middle" font-weight="bold">5. Entrega ao usuário (servicos.py)</text>
 <rect x="268" y="266" width="190" height="70" rx="8" fill="#fff" stroke="#F08A24"/>
 <text x="363" y="290" text-anchor="middle" font-weight="bold">Painel Streamlit</text>
 <text x="363" y="308" text-anchor="middle">boletim 09h · salas</text><text x="363" y="324" text-anchor="middle">panorama · calculadora</text>
 <rect x="475" y="266" width="190" height="70" rx="8" fill="#fff" stroke="#2E7DA6"/>
 <text x="570" y="290" text-anchor="middle" font-weight="bold">Menu de terminal</text>
 <text x="570" y="308" text-anchor="middle">cli.py — laços, decisões,</text><text x="570" y="324" text-anchor="middle">validação de entrada</text>
 <rect x="682" y="266" width="190" height="70" rx="8" fill="#fff" stroke="#D63E2F"/>
 <text x="777" y="290" text-anchor="middle" font-weight="bold">Aviso local na sala</text>
 <text x="777" y="308" text-anchor="middle">LEDs verde/amarelo/</text><text x="777" y="324" text-anchor="middle">vermelho + buzzer</text>
 <line x1="810" y1="170" x2="810" y2="228" stroke="#555" marker-end="url(#s)"/>
 <line x1="590" y1="170" x2="590" y2="228" stroke="#555" marker-end="url(#s)"/>
 <path d="M105,170 L105,366 L777,366 L777,338" fill="none" stroke="#D63E2F" stroke-dasharray="4 3" marker-end="url(#s)"/>
 <text x="112" y="215" fill="#D63E2F">o ESP32 avisa</text><text x="112" y="230" fill="#D63E2F">mesmo sem internet</text>
</svg>"""

# ------------------------------------------------------------------ tabelas de texto
PROPOSTAS = [
    ("Relevância social do problema", 5, 4, 4),
    ("Clareza do público beneficiado", 5, 4, 5),
    ("Disponibilidade de dados confiáveis", 5, 2, 3),
    ("Viabilidade de implementação", 5, 4, 3),
    ("Protótipo funcional demonstrável", 5, 4, 3),
    ("Aplicação coerente de Python", 5, 5, 4),
    ("Análise de dados e ML com justificativa", 5, 3, 3),
    ("Potencial de demonstração em vídeo", 5, 4, 4),
    ("Relação com os ODS", 5, 4, 4),
    ("Originalidade e diferencial", 4, 2, 3),
    ("Complexidade compatível com o prazo", 4, 4, 3),
    ("Resultados mensuráveis", 5, 4, 3),
]
tot = [sum(p[i] for p in PROPOSTAS) for i in (1, 2, 3)]
tab_prop = ("<table><caption>Tabela 1 — Avaliação comparativa das propostas (escala 1 a 5, "
            "avaliação da equipe)</caption><thead><tr><th>Critério</th><th>A · Brisa (calor nas escolas)</th>"
            "<th>B · Consumo de água em moradias populares</th><th>C · Acessibilidade de paradas de ônibus</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{e(c)}</td><td>{a}</td><td>{b}</td><td>{d}</td></tr>" for c, a, b, d in PROPOSTAS)
            + f"<tr class='total'><td>Total (máx. 60)</td><td>{tot[0]}</td><td>{tot[1]}</td><td>{tot[2]}</td></tr></tbody></table>")

DISCIPLINAS = [
    ("Lógica e programação em Python", "Funções, laços, condicionais, dicionários, listas, tratamento de exceções e leitura de arquivos CSV/JSONL", "cli.py, sensor.py, indice_calor.py"),
    ("Estatística", "Média, desvio-padrão, mediana, percentil 95, correlação de Pearson, teste t de Welch", "analise.py, notebook"),
    ("Análise e tratamento de dados (Pandas/NumPy/Matplotlib/Seaborn)", "Limpeza, interpolação, agregações, tabelas dinâmicas, 8 gráficos", "dados.py, analise.py"),
    ("Machine Learning (regressão e classificação)", "Regressão Linear e Random Forest; Regressão Logística, Árvore e Random Forest; validação temporal; métricas", "modelo.py"),
    ("Banco de dados", "Modelo relacional, DDL, chaves estrangeiras, CHECK, UNIQUE, índices, consultas com JOIN e agregação", "banco.py, brisa.db"),
    ("Sensores e IoT (ESP32)", "DHT22, LEDs, buzzer, Wi-Fi/NTP, serialização JSON, cálculo embarcado", "src/esp32/"),
    ("UX e produto", "Persona, jornada, boletim acionável, código de cores por faixa, linguagem simples", "app.py"),
    ("Sustentabilidade e ODS", "ODS 3, 4, 11 e 13, metas e indicadores de impacto", "Seções 1.5 e 4.3"),
]
tab_disc = ("<table><caption>Tabela 2 — Integração entre disciplinas</caption><thead><tr><th>Disciplina</th>"
            "<th>O que foi aplicado</th><th>Onde</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td><code>{e(c)}</code></td></tr>" for a, b, c in DISCIPLINAS)
            + "</tbody></table>")

KPIS = [
    ("Horas de aula em Cautela extrema ou pior, por sala", "Sensores (tabela leituras)", "Redução, após adaptações físicas"),
    ("Tempo de antecedência do aviso", "Boletim das 09h → pico 12h-17h", "≥ 3 horas"),
    ("Recall do aviso de Perigo em produção", "Previsões x leituras reais", "≥ 85%, com precisão monitorada"),
    ("% de alertas com ação registrada", "Novo campo 'acao_tomada' na tabela alertas", "≥ 80%"),
    ("Atendimentos por mal-estar ligado ao calor na escola", "Registro da secretaria", "Queda em relação ao ano anterior"),
    ("Aulas de educação física remanejadas (e não canceladas)", "Registro da coordenação", "Acompanhamento"),
    ("Faltas em dias de Perigo", "Diário de classe", "Comparação com dias amenos"),
]
tab_kpi = ("<table><caption>Tabela 9 — Indicadores propostos para medir o impacto (resultados esperados, "
           "ainda não medidos)</caption><thead><tr><th>Indicador</th><th>Fonte</th><th>Meta de referência</th></tr></thead><tbody>"
           + "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td></tr>" for a, b, c in KPIS)
           + "</tbody></table>")

REFS = [
    "BREIMAN, L. Random Forests. <i>Machine Learning</i>, v. 45, p. 5-32, 2001. DOI: 10.1023/A:1010933404324.",
    "EXAME. Brasil registra o ano mais quente da história em 2024. Reportagem com dados do INMET, jan. 2025. Disponível em: https://exame.com/esg/brasil-registra-o-ano-mais-quente-da-historia-em-2024. Acesso em: 17 nov. 2026.",
    "HERSBACH, H. et al. The ERA5 global reanalysis. <i>Quarterly Journal of the Royal Meteorological Society</i>, v. 146, p. 1999-2049, 2020. DOI: 10.1002/qj.3803.",
    "MONTEIRO DOS SANTOS, D. et al. Twenty-first-century demographic and social inequalities of heat-related deaths in Brazilian urban areas. <i>PLOS ONE</i>, v. 19, n. 1, e0295766, 2024. DOI: 10.1371/journal.pone.0295766. Acesso em: 17 nov. 2026.",
    "MUÑOZ-SABATER, J. et al. ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. <i>Earth System Science Data</i>, v. 13, p. 4349-4383, 2021. DOI: 10.5194/essd-13-4349-2021.",
    "NATIONAL WEATHER SERVICE (NWS). <i>Heat Index</i>. Disponível em: https://www.weather.gov/safety/heat-index. Acesso em: 17 nov. 2026.",
    "NWS WEATHER PREDICTION CENTER. <i>The Heat Index Equation</i>. Disponível em: https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml. Acesso em: 17 nov. 2026.",
    "ONU BRASIL. <i>Objetivos de Desenvolvimento Sustentável</i>. Disponível em: https://brasil.un.org/pt-br/sdgs. Acesso em: 17 nov. 2026.",
    "OPEN-METEO. <i>Historical Weather API</i>. Disponível em: https://open-meteo.com/en/docs/historical-weather-api. Acesso em: 17 nov. 2026.",
    "PEDREGOSA, F. et al. Scikit-learn: Machine Learning in Python. <i>Journal of Machine Learning Research</i>, v. 12, p. 2825-2830, 2011.",
    "REVISTA PESQUISA FAPESP. Aquecimento global amplifica ondas de calor que podem assolar cidades brasileiras até 15 vezes ao ano. 2025. Disponível em: https://revistapesquisa.fapesp.br/aquecimento-global-amplifica-ondas-de-calor-que-podem-assolar-cidades-brasileiras-ate-15-vezes-ao-ano/. Acesso em: 17 nov. 2026.",
    "ROTHFUSZ, L. P. <i>The Heat Index \"Equation\" (or, More Than You Ever Wanted to Know About Heat Index)</i>. NWS Southern Region Technical Attachment SR 90-23. Fort Worth: National Weather Service, 1990.",
    "UNICEF. <i>Learning interrupted: Global snapshot of climate-related school disruptions in 2024</i>. Nova York: UNICEF, jan. 2025. Disponível em: https://www.unicef.org/reports/learning-interrupted-global-snapshot-2024. Acesso em: 17 nov. 2026.",
    "UNICEF BRASIL. Quase 250 milhões de crianças e adolescentes tiveram os estudos interrompidos por crises climáticas em 2024, alerta UNICEF. Comunicado de imprensa, jan. 2025. Disponível em: https://www.unicef.org/brazil/comunicados-de-imprensa. Acesso em: 17 nov. 2026.",
    "ZIPPENFENIG, P. <i>Open-Meteo.com Weather API</i> [software]. Zenodo, 2023. DOI: 10.5281/zenodo.7970649.",
]

# ------------------------------------------------------------------ tabelas de resultados
t_desc = tabela(an["descritivas"], ["cidade", "media", "desvio_padrao", "mediana", "p95", "maximo", "pct_horas_alerta"],
                ["Cidade", "Média", "Desvio", "Mediana", "P95", "Máximo", "% horas ≥ 32,2 °C"],
                "Tabela 4 — Índice de calor (°C) em horário escolar, 2020-2025 (dados reais ERA5)")
t_horas = tabela(an["horas_alerta_ano"], ["cidade", "2020", "2021", "2022", "2023", "2024", "2025"],
                 ["Cidade", "2020", "2021", "2022", "2023", "2024", "2025"],
                 "Tabela 5 — Horas de aula por ano com índice de calor ≥ 32,2 °C")
t_crit = tabela(an["dias_criticos_ano"], ["cidade", "2020", "2021", "2022", "2023", "2024", "2025"],
                ["Cidade", "2020", "2021", "2022", "2023", "2024", "2025"],
                "Tabela 5b — Dias letivos críticos (≥ 4 horas de aula com índice ≥ 32,2 °C)")
t_per = tabela(an["comparacao_periodos"], ["cidade", "media_2020_2022", "media_2023_2025", "diferenca", "t", "p_valor"],
               ["Cidade", "Média 2020-22 (°C)", "Média 2023-25 (°C)", "Diferença", "t", "p-valor"],
               "Tabela 6 — Pico diário do índice de calor em dias úteis: teste t de Welch")
t_reg = tabela(reg, ["modelo", "MAE", "RMSE", "R2"], ["Modelo", "MAE (°C)", "RMSE (°C)", "R²"],
               "Tabela 7 — Regressão do pico da tarde, teste 2024-2025 (2.615 dias)")
t_clf = tabela(clf, ["modelo", "acuracia", "f1_macro", "recall_cautela_extrema", "recall_perigo"],
               ["Modelo", "Acurácia", "F1-macro", "Recall C. extrema", "Recall Perigo"],
               "Tabela 8 — Classificação da faixa de risco da tarde, teste 2024-2025")
t_classe = tabela([{"classe": k, **{a: round(b, 3) for a, b in rep[k].items()}} for k in ["Normal", "Cautela", "Cautela extrema", "Perigo"]],
                  ["classe", "precision", "recall", "f1-score", "support"],
                  ["Faixa", "Precisão", "Recall", "F1", "Dias"], "Tabela 8b — Random Forest por classe (teste)")
t_cid = tabela(met["classificacao_por_cidade"], ["cidade", "acuracia", "dias"], ["Cidade", "Acurácia", "Dias de teste"],
               "Tabela 8c — Acurácia do classificador por cidade (teste)")
t_demo = tabela(prev_demo, ["data", "pico_previsto", "faixa_prevista", "prob_perigo", "pico_observado", "faixa_observada"],
                ["Dia", "Pico previsto (°C)", "Faixa prevista", "P(Perigo)", "Pico observado (°C)", "Faixa observada"],
                "Tabela 10 — Boletins das 09h da semana de demonstração (Rio de Janeiro, fev. 2025, dados reais)")
t_amb = tabela(resumo_demo, ["ambiente", "ic_medio", "ic_maximo", "minutos_em_alerta", "minutos_em_perigo"],
               ["Ambiente (SIMULADO)", "IC médio", "IC máximo", "min ≥ 32,2 °C", "min ≥ 39,4 °C"],
               "Tabela 11 — Ambientes da escola fictícia na semana simulada (5 dias, 7h-17h)")
t_cat = tabela(an["categorias_pct"], ["cidade", "Normal", "Cautela", "Cautela extrema", "Perigo"],
               ["Cidade", "Normal", "Cautela", "Cautela extrema", "Perigo"],
               "Tabela 4b — Distribuição (%) das horas de aula por faixa de risco")

val = an["validacao_indice"]
integrantes = "".join(f"<li>{e(i['nome'])} — {e(i['rm'])}</li>" for i in equipe["integrantes"])

# ------------------------------------------------------------------ HTML
CSS = """
@page { size: A4; margin: 22mm 20mm 20mm 22mm;
  @bottom-right { content: counter(page); font: 9pt Helvetica, Arial, sans-serif; color: #888; }
  @bottom-left { content: "Brisa · FIAP Global Solution 2026.2"; font: 8pt Helvetica, Arial, sans-serif; color: #aaa; } }
@page :first { @bottom-right { content: none; } @bottom-left { content: none; } }
* { box-sizing: border-box; }
body { font: 10.5pt/1.5 Georgia, 'Times New Roman', serif; color: #1d1d1f; margin: 0; }
h1, h2, h3, h4, caption, figcaption, th, .capa, .kpi, .box { font-family: Helvetica, Arial, sans-serif; }
h1 { font-size: 19pt; color: #7A1F3D; margin: 0 0 10pt; page-break-before: always; border-bottom: 2px solid #F08A24; padding-bottom: 4pt; }
h2 { font-size: 13pt; color: #2E7DA6; margin: 16pt 0 6pt; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; page-break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 8pt 16pt; padding: 0; } li { margin-bottom: 2pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 12pt; font: 8.6pt/1.35 Helvetica, Arial, sans-serif; page-break-inside: avoid; }
caption { caption-side: top; text-align: left; font-weight: bold; font-size: 8.8pt; color: #444; padding-bottom: 4pt; }
th { background: #2E7DA6; color: #fff; text-align: left; padding: 4pt 5pt; font-weight: 600; }
td { border-bottom: 1px solid #e3e3e3; padding: 3pt 5pt; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fb; } tr.total td { font-weight: bold; background: #FFF4E6; }
figure { margin: 8pt 0 12pt; page-break-inside: avoid; }
figure.img { text-align: center; } figure.img img { max-width: 100%; border: 1px solid #eee; }
figcaption { font-size: 8.6pt; color: #555; margin-top: 3pt; }
figure.code figcaption { margin: 0 0 3pt; font-weight: bold; }
pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-left: 3px solid #F08A24; padding: 7pt 9pt;
      font: 7.6pt/1.4 Menlo, Consolas, monospace; white-space: pre-wrap; word-break: break-word; margin: 0; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.5pt; }
td code { font-size: 7.6pt; }
.capa { height: 250mm; display: flex; flex-direction: column; justify-content: space-between; }
.capa .topo { font-size: 10pt; color: #555; letter-spacing: .5px; }
.capa .titulo { font-size: 40pt; font-weight: 800; color: #7A1F3D; margin: 0; }
.capa .sub { font-size: 14pt; color: #2E7DA6; margin: 4pt 0 24pt; }
.capa .faixa { height: 10px; background: linear-gradient(90deg,#2E9E6B,#E8C547,#F08A24,#D63E2F,#7A1F3D); border-radius: 5px; margin: 14pt 0; }
.capa ul { list-style: none; margin: 0; font-size: 11pt; } .capa li { margin: 3pt 0; }
.capa .rot { font-size: 9pt; text-transform: uppercase; color: #888; margin-top: 14pt; letter-spacing: .6px; }
.capa .links { font-size: 9.5pt; word-break: break-all; }
.kpis { display: flex; gap: 8pt; margin: 8pt 0 12pt; }
.kpi { flex: 1; border: 1px solid #e3e3e3; border-top: 4px solid #F08A24; border-radius: 6px; padding: 7pt; }
.kpi b { display: block; font-size: 16pt; color: #7A1F3D; } .kpi span { font-size: 8pt; color: #555; }
.box { border-radius: 6px; padding: 8pt 10pt; margin: 8pt 0 12pt; font-size: 9pt; line-height: 1.45; page-break-inside: avoid; }
.box.sim { background: #FFF4E6; border: 1px solid #F7C38A; } .box.info { background: #E8F4FA; border: 1px solid #A9D3E8; }
.box.ok { background: #EEF7F0; border: 1px solid #A8D8B9; }
.toc { columns: 2; font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; } .toc div { margin: 2pt 0; }
.duas { display: flex; gap: 10pt; } .duas > * { flex: 1; }
.refs p { text-align: left; padding-left: 14pt; text-indent: -14pt; font-size: 9pt; }
.ev { font: 7pt/1.35 Menlo, monospace; }
"""

H = []
H.append(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Brisa — Relatório GS 2026.2</title>
<style>{CSS}</style></head><body>
<section class="capa">
 <div>
  <div class="topo">FIAP · GRADUAÇÃO EM INTELIGÊNCIA ARTIFICIAL · GLOBAL SOLUTION 2026.2 · CITIZENTECH</div>
  <div class="faixa"></div>
  <p class="titulo">Brisa</p>
  <p class="sub">Calor seguro na escola: previsão com IA, sensores nas salas e<br>recomendações para proteger estudantes durante o calor extremo</p>
  <div class="rot">Integrantes</div><ul>{integrantes}</ul>
  <div class="rot">Turma</div><ul><li>1TIAO · Graduação em Inteligência Artificial (FIAP ON) · 1º ano, Fase 3</li></ul>
 </div>
 <div>
  <div class="rot">Links para correção</div>
  <ul class="links"><li><b>Vídeo (YouTube, não listado):</b> {e(equipe['link_video'])}</li>
  <li><b>Repositório GitHub (privado, compartilhado com fiap-tutoria):</b> {e(equipe['link_github'])}</li>
  <li><b>Pasta da entrega no repositório:</b> FIAP-PORTFOLIO-AI/1TIAO/GLOBAL-SOLUTION-1</li></ul>
  <div class="faixa"></div>
  <div class="topo">São Paulo · novembro de 2026</div>
 </div>
</section>

<h1 style="page-break-before:always">Sumário</h1>
<div class="toc">
<div><b>Resumo</b></div>
<div><b>1 Introdução</b></div><div>1.1 Contexto</div><div>1.2 Problema</div><div>1.3 Público beneficiado</div><div>1.4 Objetivos</div><div>1.5 ODS relacionados</div>
<div><b>2 Desenvolvimento</b></div><div>2.1 Escolha estratégica do projeto</div><div>2.2 Fundamentação e soluções existentes</div>
<div>2.3 A solução Brisa</div><div>2.4 Arquitetura</div><div>2.5 Dados: origem, tratamento e limitações</div><div>2.6 Índice de calor</div>
<div>2.7 Análise estatística</div><div>2.8 Machine Learning</div><div>2.9 Banco de dados</div><div>2.10 Sensores e ESP32</div>
<div>2.11 Interfaces</div><div>2.12 Integração entre disciplinas</div>
<div><b>3 Resultados obtidos</b></div><div>3.1 Exposição ao calor nas escolas</div><div>3.2 Desempenho dos modelos</div>
<div>3.3 Demonstração integrada</div><div>3.4 Testes e evidências</div>
<div><b>4 Conclusões</b></div><div>4.1 Síntese</div><div>4.2 Limitações</div><div>4.3 Medição de impacto</div><div>4.4 Próximos passos</div>
<div><b>Referências</b></div><div><b>Apêndice A</b>: como executar</div><div><b>Apêndice B</b>: checklist dos requisitos da FIAP</div>
</div>

<h2>Resumo</h2>
<p>O calor extremo deixou de ser um desconforto ocasional e passou a interromper a escolarização: em 2024, ondas de calor foram o evento climático
que mais afetou estudantes no mundo, com cerca de 171 milhões atingidos (UNICEF, 2025). Este trabalho apresenta o <b>Brisa</b>, uma prova de conceito
que ajuda a coordenação de escolas públicas a <b>antecipar</b> e <b>gerenciar</b> o calor durante as aulas. Com dados meteorológicos <b>reais</b>
(Open-Meteo/ERA5, horários, 2020-2025) de cinco capitais brasileiras, medimos quanto do tempo de aula passa em faixas de risco do índice de calor do
NWS/NOAA e treinamos modelos que, às 09h, preveem o pico do índice entre 12h e 17h. O Random Forest obteve MAE de {fmt(rf_reg['MAE'])} °C e R² de
{fmt(rf_reg['R2'])} na regressão, e acurácia de {pct(rf_clf['acuracia'])} na classificação da faixa, em teste fora da amostra (2024-2025), superando a linha
de base de persistência. O protótipo inclui firmware para ESP32 com sensor DHT22, banco SQLite com regras de integridade, motor de alertas, menu de
terminal e painel web. A demonstração integrada usa uma escola <b>fictícia</b> com leituras internas <b>simuladas</b>, identificadas como tais. O projeto
se relaciona aos ODS 3, 4, 11 e 13 e propõe indicadores para medir seu impacto num piloto real.</p>
<div class="kpis">
 <div class="kpi"><b>{desc['Teresina (PI)']['pct_horas_alerta']:.0f}%</b><span>das horas de aula em Teresina com índice ≥ 32,2 °C</span></div>
 <div class="kpi"><b>{fmt(rf_reg['MAE'])} °C</b><span>erro médio do pico previsto às 09h (teste 2024-25)</span></div>
 <div class="kpi"><b>{pct(rf_clf['acuracia'])}</b><span>acurácia da faixa de risco prevista</span></div>
 <div class="kpi"><b>{n_testes}/{n_testes}</b><span>testes automatizados aprovados</span></div>
</div>
<p><b>Palavras-chave:</b> calor extremo; escolas; índice de calor; Random Forest; ESP32; CitizenTech.</p>
""")

# ---------------- 1 Introdução
H.append(f"""
<h1>1 Introdução</h1>
<h2>1.1 Contexto</h2>
<p>O Brasil vive anos seguidos de recordes de temperatura. Segundo dados do INMET divulgados em janeiro de 2025, 2024 foi o ano mais quente da série
histórica do país, superando 2023 (EXAME, 2025). Um estudo do INPE citado pela Revista Pesquisa FAPESP (2025) indica que o número médio de dias com
ondas de calor passou de cerca de 7 por ano (1961-1990) para 52 por ano (2011-2020). O calor tem custo humano: Monteiro dos Santos <i>et al.</i> (2024)
estimaram 48.075 mortes atribuíveis a ondas de calor entre 2000 e 2018 em 14 regiões metropolitanas brasileiras, com efeito maior entre idosos,
mulheres, pessoas pretas e pardas e pessoas com menor escolaridade.</p>
<p>A escola sente esse efeito todos os dias. O relatório <i>Learning Interrupted</i> (UNICEF, 2025) contabilizou pelo menos 242 milhões de estudantes
em 85 países ou territórios com aulas afetadas por eventos climáticos em 2024, e as ondas de calor foram o principal fator, com cerca de 171 milhões de estudantes
atingidos. A própria publicação ressalta que a estimativa é conservadora por limitações de dados.</p>

<h2>1.2 Problema</h2>
<p>Hoje, a decisão de adaptar a rotina escolar ao calor costuma ser <b>reativa e subjetiva</b>. Os avisos meteorológicos são regionais e chegam como
"onda de calor nos próximos dias", sem dizer <b>qual sala</b> estará perigosa <b>em qual horário</b> nem <b>o que fazer</b>. Salas no último andar ou sob
telhado de fibrocimento podem ficar bem mais quentes que o ambiente externo, e a coordenação só percebe quando alguém passa mal.</p>
<div class="box info"><b>Pergunta norteadora:</b> como a IA e a análise de dados, combinadas a sensores de baixo custo e a um banco de dados simples,
podem avisar a escola <b>com horas de antecedência</b> e orientar ações concretas para proteger estudantes do calor extremo?</div>

<h2>1.3 Público beneficiado</h2>
<ul>
<li><b>Beneficiários diretos:</b> crianças e adolescentes da rede pública, mais sensíveis ao calor e dependentes de decisões dos adultos;
professores e funcionários, expostos às mesmas condições.</li>
<li><b>Usuária principal (persona):</b> <i>coordenadora pedagógica</i> de uma escola municipal, sem formação técnica, que precisa decidir até o intervalo
da manhã se mantém a educação física na quadra, se troca turmas de sala e se avisa as famílias.</li>
<li><b>Beneficiários indiretos:</b> famílias, que recebem orientações claras, e secretarias de educação, que ganham dados para priorizar reformas
(ventilação, sombreamento e isolamento térmico) nas escolas mais críticas.</li>
</ul>

<h2>1.4 Objetivos</h2>
<p><b>Objetivo geral:</b> desenvolver uma prova de conceito que transforme dados meteorológicos e leituras de sensores em avisos antecipados e
recomendações práticas sobre o calor em escolas.</p>
<p><b>Objetivos específicos:</b></p>
<ol>
<li>Quantificar, com dados reais, a exposição ao calor em horário escolar em cinco capitais de regiões diferentes.</li>
<li>Treinar e avaliar modelos de regressão e classificação que, às 09h, prevejam o pico do índice de calor da tarde e sua faixa de risco.</li>
<li>Implementar firmware para ESP32 que meça, classifique e sinalize o risco dentro da sala.</li>
<li>Persistir escolas, ambientes, leituras, alertas e previsões em um banco relacional com regras de integridade.</li>
<li>Oferecer interfaces (painel web e menu) que traduzam números em ações, e testar automaticamente os componentes críticos.</li>
</ol>

<h2>1.5 ODS relacionados</h2>
<table><caption>Tabela 3 — Objetivos de Desenvolvimento Sustentável e contribuição do Brisa</caption>
<thead><tr><th>ODS</th><th>Meta relacionada (ONU)</th><th>Contribuição do Brisa</th></tr></thead><tbody>
<tr><td><b>3</b> Saúde e bem-estar</td><td>3.d: reforçar a capacidade de alerta precoce e de gestão de riscos à saúde</td><td>Aviso às 09h e alerta em tempo real por sala antes de o risco se materializar</td></tr>
<tr><td><b>4</b> Educação de qualidade</td><td>4.a: ambientes de aprendizagem seguros, não violentos, inclusivos e eficazes</td><td>Dados por sala para priorizar reformas; aulas remanejadas em vez de canceladas</td></tr>
<tr><td><b>11</b> Cidades e comunidades sustentáveis</td><td>11.5: reduzir mortes e pessoas afetadas por desastres</td><td>Ondas de calor são desastres: a escola vira ponto de monitoramento e de proteção</td></tr>
<tr><td><b>13</b> Ação contra a mudança do clima</td><td>13.1: resiliência e adaptação a riscos climáticos; 13.3: educação sobre o clima</td><td>Adaptação local de baixo custo; o painel pode ser usado em aula para discutir clima com dados reais</td></tr>
</tbody></table>
""")

# ---------------- 2 Desenvolvimento
H.append(f"""
<h1>2 Desenvolvimento</h1>
<h2>2.1 Escolha estratégica do projeto</h2>
<p>Antes de desenvolver, a equipe avaliou três propostas compatíveis com o desafio CitizenTech, usando 12 critérios pontuados de 1 a 5:</p>
<ul>
<li><b>A · Brisa:</b> previsão e monitoramento do calor em escolas (dados meteorológicos reais + ML + ESP32 + banco).</li>
<li><b>B · Consumo de água em moradias populares:</b> análise de registros de hidrômetro para detectar vazamentos e desperdício.</li>
<li><b>C · Acessibilidade de paradas de ônibus:</b> cadastro e análise da acessibilidade das paradas para pessoas com deficiência.</li>
</ul>
{tab_prop}
<p><b>Decisão:</b> a proposta A teve a maior pontuação ({tot[0]}/60). Ela combina um problema grave e crescente, um público bem definido e
<b>dados públicos reais e completos</b>, o que permite treinar e avaliar ML com honestidade, além de usar ESP32 e banco de dados de forma natural, sem
forçar tecnologia. A proposta B dependeria quase só de dados simulados, porque não há bases públicas de consumo residencial em alta frequência. A C
exigiria coleta de campo extensa e oferece pouco espaço para ML justificável.</p>

<h2>2.2 Fundamentação e soluções existentes</h2>
<p><b>O que já existe:</b> o INMET publica avisos meteorológicos de onda de calor por região; a Defesa Civil envia alertas por SMS; aplicativos de previsão
mostram a "sensação térmica" da cidade. São serviços valiosos, mas pensados para a população em geral.</p>
<p><b>Lacunas identificadas:</b> (1) a escala é a cidade ou a região, não a sala de aula; (2) não medem o ambiente interno, onde estudantes passam o dia;
(3) não traduzem o risco em decisões da rotina escolar; (4) não geram histórico por escola para orientar investimentos.</p>
<p><b>Oportunidade:</b> combinar a previsão (boletim das 09h, com dados abertos) e a medição (sensor barato por ambiente) num fluxo único de decisão,
com recomendações operacionais e registro em banco.</p>

<h2>2.3 A solução Brisa</h2>
<p><b>Proposta de valor:</b> <i>"Saiba às 9h se a tarde será perigosa, veja qual sala está mais quente agora e o que fazer."</i></p>
<p><b>Identidade:</b> o nome remete ao alívio do calor. A paleta segue as cinco faixas do índice (verde, amarelo, laranja, vermelho e vinho), um código de
cores intuitivo e consistente no painel, nos LEDs do ESP32 e nos gráficos.</p>
<p><b>Fluxo de uso (jornada da coordenação):</b></p>
<ol>
<li><b>09h:</b> o Brisa lê as condições da manhã e publica o boletim com o pico previsto, a faixa de risco, as probabilidades e as ações recomendadas.</li>
<li><b>Durante a tarde:</b> cada sala com ESP32 sinaliza localmente (LEDs e buzzer) e envia leituras. O backend valida, grava e alerta quando o risco sobe.</li>
<li><b>Decisão:</b> o painel mostra o ambiente mais fresco para receber turmas e o histórico de alertas.</li>
<li><b>Gestão:</b> os minutos em alerta por sala viram evidência para pedir reformas à secretaria.</li>
</ol>

<h2>2.4 Arquitetura</h2>
<figure class="img">{ARQ_SVG}<figcaption>Figura 1 — Arquitetura do Brisa: fontes de dados, tratamento, inteligência, persistência e entrega ao usuário.</figcaption></figure>
<p>O código fica num pacote Python (<code>src/brisa</code>) com módulos de responsabilidade única. O menu de terminal, o painel web e o notebook chamam as
mesmas funções, o que evita duplicação e facilita os testes. A arquitetura é deliberadamente simples: arquivos CSV, SQLite e um processo Python
bastam para uma escola ou uma pequena rede.</p>

<h2>2.5 Dados: origem, tratamento e limitações</h2>
<h3>Dados reais</h3>
<p>Usamos a API de histórico da <b>Open-Meteo</b>, que disponibiliza a reanálise <b>ERA5/ERA5-Land</b> do Copernicus/ECMWF (Hersbach <i>et al.</i>, 2020;
Muñoz-Sabater <i>et al.</i>, 2021; Zippenfenig, 2023). Baixamos séries <b>horárias</b> de 01/01/2020 a 31/12/2025 para São Paulo, Rio de Janeiro,
Cuiabá, Teresina e Manaus (uma capital por região) com temperatura a 2 m, umidade relativa, sensação térmica, vento a 10 m e radiação solar,
no fuso America/Sao_Paulo. Total: <b>263.040 registros</b> (52.608 por cidade). Data da coleta: 17/11/2026.</p>
<h3>Tratamento</h3>
<ol>
<li>Leitura dos CSV ignorando as 3 linhas de metadados e padronização dos nomes de colunas.</li>
<li>Remoção de duplicatas (cidade + horário) e anulação de valores fisicamente impossíveis (ex.: temperatura fora de -10 a 50 °C).</li>
<li>Interpolação linear de lacunas de até 3 horas, por cidade; descarte do que restasse sem temperatura ou umidade.</li>
<li>Cálculo do índice de calor e da faixa de risco; marcação de <b>horário escolar</b> (segunda a sexta, 7h às 17h).</li>
<li>Montagem do dataset diário de ML (7.825 dias úteis), com atributos só até as 09h.</li>
</ol>
<p>Resultado do tratamento: 0 duplicatas, 0 valores fora da faixa e 0 nulos. A ERA5 entrega séries completas, mas as regras continuam no código
(e testadas) para dados de sensores, que costumam ter falhas.</p>
<div class="box sim"><b>Dados simulados, claramente identificados.</b> A escola "Escola Municipal Demonstração Brisa" e seus três ambientes são
<b>fictícios</b>. As leituras internas foram <b>simuladas</b> a cada 10 minutos: temperatura interna = temperatura externa <u>real</u> + aquecimento
<u>hipotético</u> (0,5 a 1,5 °C + 1,0 a 3,5 °C por kW/m² de radiação solar, conforme o ambiente) + ruído; umidade interna = externa − 2 a 5 pontos.
Essas hipóteses servem apenas para demonstrar o fluxo e <b>não</b> foram calibradas com medições reais. No banco, essas linhas têm
<code>origem = 'simulado'</code>.</div>
<p><b>Limitações dos dados:</b> a ERA5 é uma grade de ~9 a 25 km e não captura ilhas de calor de bairro nem o interior das salas; o horário escolar não
considera feriados nem férias; seis anos são pouco para afirmar tendência climática.</p>

<h2>2.6 Índice de calor</h2>
<p>O índice de calor (<i>heat index</i>) estima a temperatura percebida pelo corpo à sombra, combinando temperatura e umidade. Implementamos o algoritmo
oficial do NWS Weather Prediction Center: fórmula simples de Steadman e, acima de 80 °F, a regressão de Rothfusz (1990) com os dois ajustes
oficiais. Faixas usadas (convertidas de °F): <b>Normal</b> &lt; 26,7 °C; <b>Cautela</b> 26,7-32,2; <b>Cautela extrema</b> 32,2-39,4;
<b>Perigo</b> 39,4-51,7; <b>Perigo extremo</b> ≥ 51,7 °C. O Brisa alerta a partir de <i>Cautela extrema</i>.</p>
{codigo(funcao('brisa/indice_calor.py', 'indice_de_calor'), 'Código 1 — src/brisa/indice_calor.py: cálculo com validação de entrada')}
<p><b>Validação:</b> os testes conferem o resultado com valores da tabela oficial do NWS (ex.: 90 °F e 70% → 106 °F), dentro do erro de ±1,3 °F da regressão. Como
checagem independente, a correlação entre o nosso índice e a sensação térmica da Open-Meteo, calculada por outra fórmula, foi de
<b>{fmt(val['pearson_ic_vs_sensacao_openmeteo'])}</b> (Pearson) em 263 mil horas.</p>

<h2>2.7 Análise estatística</h2>
<p>Calculamos média, desvio-padrão, mediana, percentil 95 e máximo do índice em horário escolar; a distribuição por faixa; as horas e os dias
críticos por ano; a correlação de Pearson entre variáveis; e um <b>teste t de Welch</b> comparando o pico diário de 2020-2022 com o de 2023-2025. O código
fica em <code>src/brisa/analise.py</code> e é reproduzido passo a passo no notebook.</p>
{codigo(funcao('brisa/dados.py', 'limpar'), 'Código 2 — src/brisa/dados.py: limpeza com relatório do que foi tratado')}

<h2>2.8 Machine Learning</h2>
<p><b>Formulação.</b> Às 09h de cada dia útil, prever: (a) o <b>pico do índice de calor entre 12h e 17h</b> (regressão) e (b) a <b>faixa de risco</b>
desse pico (classificação em 4 classes). <b>Atributos (10):</b> temperatura, umidade e índice às 09h; temperatura às 06h; aquecimento entre 06h e 09h;
radiação acumulada na manhã; vento às 09h; pico da tarde anterior; e seno e cosseno do mês (sazonalidade). Nenhum atributo usa informação posterior às 09h,
o que é verificado por teste automatizado.</p>
<p><b>Validação.</b> A divisão é <b>temporal</b>: treino com 2020-2023 ({fmt(met['n_treino'])} dias) e teste com 2024-2025 ({fmt(met['n_teste'])} dias), simulando o uso
no futuro. Todo modelo é comparado com uma <b>linha de base de persistência</b> ("a tarde de hoje será como a de ontem"), para provar que o ML agrega
valor. Modelos comparados: Regressão Linear e Random Forest (regressão); Regressão Logística, Árvore de Decisão e Random Forest (classificação), com
pesos balanceados por causa do desbalanceamento das classes.</p>
<p><b>Aviso preventivo de Perigo.</b> A classe <i>Perigo</i> é rara e é a mais importante. Além da classe mais provável, o Brisa emite um aviso quando
P(Perigo) passa de um limiar. O limiar foi escolhido por <b>validação temporal em janela expansível</b> (2021, 2022 e 2023, cada ano previsto por um
modelo treinado com os anos anteriores) como o de maior recall entre os que mantinham precisão ≥ 35%. O conjunto de teste não foi usado nessa escolha.</p>
{codigo(funcao('brisa/servicos.py', 'boletim_do_dia'), 'Código 3 — src/brisa/servicos.py: boletim das 09h (previsão + recomendações + verificação)')}

<h2>2.9 Banco de dados</h2>
<p>O modelo relacional tem cinco tabelas: <code>escolas</code> (1:N) <code>ambientes</code> (1:N) <code>leituras</code>, além de <code>alertas</code>
(ligada a escola e, opcionalmente, a ambiente) e <code>previsoes</code> (uma por escola e dia). As regras <code>CHECK</code> recusam leituras impossíveis,
<code>UNIQUE</code> impede leituras duplicadas e as chaves estrangeiras garantem consistência. Durante os testes, descobrimos que
<code>INSERT OR IGNORE</code> do SQLite também ignoraria em silêncio violações de <code>CHECK</code>. Por isso a inserção trata apenas a duplicidade como
tolerável (Código 5).</p>
{codigo(trecho('brisa/banco.py', 'CREATE TABLE IF NOT EXISTS leituras', 'UNIQUE (ambiente_id, data_hora)\n);'), 'Código 4 — src/brisa/banco.py: tabela de leituras (DDL)', 'sql')}
{codigo(funcao('brisa/banco.py', 'inserir_leitura'), 'Código 5 — src/brisa/banco.py: inserção que só tolera duplicidade')}

<h2>2.10 Sensores e ESP32</h2>
<p>Cada ambiente recebe um ESP32 com sensor <b>DHT22</b> (temperatura e umidade), três LEDs (verde: Normal/Cautela; amarelo: Cautela extrema;
vermelho: Perigo ou pior) e um buzzer. O firmware calcula o índice de calor <b>no próprio dispositivo</b>, com a mesma fórmula do backend
(<code>brisa_ic.h</code>), para que a sala seja avisada mesmo sem internet. O horário vem por NTP e cada leitura sai pela serial como uma linha JSON.
Leituras inválidas do sensor nunca são enviadas. O backend <b>recalcula</b> o índice: não confia no dispositivo.</p>
{codigo(trecho('esp32/sketch.ino', 'void loop() {', 'brisa_categoria(nivel));\n}'), 'Código 6 — src/esp32/sketch.ino: laço principal do firmware', 'cpp')}
<p>A ingestão no backend valida cada linha (JSON bem formado, campos obrigatórios, data ISO, faixas físicas) e rejeita a linha com o motivo registrado,
sem interromper o lote:</p>
{codigo(funcao('brisa/sensor.py', 'validar_linha'), 'Código 7 — src/brisa/sensor.py: validação das leituras do ESP32')}
<p>Para não sobrecarregar a equipe com notificações, o motor de alertas só alerta a partir de <i>Cautela extrema</i>, alerta de imediato quando a
situação piora e repete a mesma faixa no máximo a cada 60 minutos, no mesmo ritmo das pausas de hidratação recomendadas:</p>
{codigo(funcao('brisa/alertas.py', 'deve_alertar'), 'Código 8 — src/brisa/alertas.py: regra de disparo de alertas')}
<div class="box ok"><b>Execução real do firmware (Wokwi, 17/11/2026):</b> o <code>sketch.ino</code> e o <code>diagram.json</code> foram
carregados no simulador Wokwi e executados. O ESP32 conectou à rede, sincronizou o relógio por NTP e enviou leituras JSON. Variamos o DHT22 de 26 °C/50% até
36 °C/60%, e os LEDs passaram de verde para amarelo e vermelho, com bipe. As 11 linhas capturadas estão em <code>docs/evidencia_wokwi_serial.jsonl</code>: o backend
aceitou todas, e o índice calculado no chip coincidiu com o do Python, com diferença &lt; 0,05 °C (<code>docs/evidencia_wokwi_ingestao.txt</code>). Além disso,
a fórmula embarcada é compilada e comparada com a versão em Python em 221 combinações nos testes automatizados. Não testamos em placa física.</div>
{fig('wokwi_perigo.png', 'Figura 1b — Firmware do Brisa rodando no Wokwi: DHT22 em 36 °C e 60% → índice 48,1 °C, faixa Perigo, LED vermelho aceso e linhas JSON no monitor serial.', '100%')}

<h2>2.11 Interfaces</h2>
<p><b>Painel web (Streamlit)</b>, para a coordenação, com quatro abas: <i>Boletim das 09h</i> (cartões com as condições da manhã, faixa prevista com cor,
o que fazer hoje, probabilidades e a curva real do dia para conferência); <i>Salas em tempo real</i> (curvas por ambiente, resumo, ambiente mais fresco
e alertas); <i>Panorama 2020-2025</i>; e <i>Calculadora</i>. <b>Menu de terminal</b> (<code>python src/main.py menu</code>), que aplica os fundamentos de
Python: laço principal, dicionário de opções, validação de entrada com <code>try/except</code> e repetição até o valor ser válido.</p>
{codigo(funcao('brisa/cli.py', 'ler_float'), 'Código 9 — src/brisa/cli.py: leitura numérica robusta no menu')}

<h2>2.12 Integração entre disciplinas</h2>
{tab_disc}
""")

# ---------------- 3 Resultados
H.append(f"""
<h1>3 Resultados obtidos</h1>
<div class="box ok">Todos os números desta seção foram produzidos pelo código do repositório (<code>python src/main.py tudo</code>) e conferidos
pela equipe. Resultados com dados <b>reais</b>: seções 3.1 e 3.2. Demonstração com escola <b>fictícia</b> e leituras <b>simuladas</b>: seção 3.3.</div>
<h2>3.1 Exposição ao calor nas escolas (dados reais, 2020-2025)</h2>
{t_desc}
{t_cat}
{fig('fig_categorias_cidades.png', 'Figura 2 — Faixas de risco nas horas de aula por cidade.', '92%')}
<p>Em <b>Teresina</b>, {desc['Teresina (PI)']['pct_horas_alerta']:.1f}% das horas de aula ficaram em <i>Cautela extrema</i> ou pior; em Manaus, {desc['Manaus (AM)']['pct_horas_alerta']:.1f}%; e em
Cuiabá, {desc['Cuiabá (MT)']['pct_horas_alerta']:.1f}%. No Rio de Janeiro, a mediana é moderada ({desc['Rio de Janeiro (RJ)']['mediana']} °C), mas a cauda é longa: o máximo chegou a
{desc['Rio de Janeiro (RJ)']['maximo']} °C, em faixa de <i>Perigo</i>, o que mostra a importância de <b>prever</b> os dias excepcionais. Em São Paulo o risco externo é
baixo ({desc['São Paulo (SP)']['pct_horas_alerta']}%), mas salas mal ventiladas podem ficar acima disso, e é aí que entra o sensor.</p>
{fig('fig_boxplot_cidades.png', 'Figura 3 — Distribuição do índice de calor em horário escolar, com os limiares das faixas.', '92%')}
{t_horas}
{fig('fig_horas_alerta_ano.png', 'Figura 4 — Horas de aula por ano em Cautela extrema ou pior.', '88%')}
{t_crit}
{fig('fig_mapa_mes_hora.png', 'Figura 5 — Índice de calor médio por mês e hora (Rio de Janeiro e Cuiabá): o risco se concentra entre 11h e 16h.', '96%')}
{t_per}
<p>O pico diário médio foi de 1,0 a 1,4 °C maior em 2023-2025 do que em 2020-2022 nas cinco cidades (p &lt; 0,001). <b>Cautela na interpretação:</b>
o período inclui o El Niño forte de 2023-2024, e seis anos não bastam para estimar tendência climática. O resultado descreve o período, não prova
causa.</p>
{fig('fig_correlacao.png', 'Figura 6 — Correlação de Pearson: o índice depende sobretudo da temperatura e, em segundo plano, da radiação.', '60%')}

<h2>3.2 Desempenho dos modelos (teste fora da amostra, 2024-2025)</h2>
{t_reg}
<p>O <b>Random Forest</b> reduziu o erro médio absoluto do pico de {fmt(base_reg['MAE'])} °C (persistência) para <b>{fmt(rf_reg['MAE'])} °C</b>
({(1 - rf_reg['MAE'] / base_reg['MAE']) * 100:.0f}% menor), com R² = {fmt(rf_reg['R2'])}.</p>
{fig('fig_regressao_pico.png', 'Figura 7 — Pico observado e pico previsto às 09h (Random Forest, teste 2024-2025).', '62%')}
{t_clf}
<div class="duas">{t_classe}{t_cid}</div>
{fig('fig_matriz_confusao.png', 'Figura 8 — Matriz de confusão do classificador Random Forest no teste.', '58%')}
<p>O Random Forest teve a melhor acurácia ({pct(rf_clf['acuracia'])}) e o melhor F1-macro ({fmt(rf_clf['f1_macro'])}). Seu ponto fraco é a classe <i>Perigo</i>
(recall {pct(rf_clf['recall_perigo'])}). Por isso existe o aviso preventivo: com o limiar de {fmt(ap['limiar_probabilidade'])} definido na validação, o recall de
<i>Perigo</i> no teste subiu para <b>{pct(ap['recall_teste'])}</b> ({round(ap['recall_teste'] * ap['dias_perigo_reais_teste'])} de {ap['dias_perigo_reais_teste']} dias), com precisão de
{pct(ap['precisao_teste'])} ({ap['alertas_emitidos_teste']} avisos). A precisão no teste ficou abaixo da observada na validação, sinal de mudança na distribuição entre os
períodos. Mantivemos o aviso porque ele pede só <b>vigilância</b> (acompanhar sensores e preparar o remanejamento), uma ação de baixo custo diante do risco
de não avisar. Ainda assim, a precisão precisa ser monitorada num piloto.</p>
{fig('fig_importancia_atributos.png', 'Figura 9 — Importância dos atributos (Random Forest, regressão): temperatura e índice às 09h dominam.', '64%')}

<h2>3.3 Demonstração integrada (escola fictícia, semana real de calor)</h2>
<p>A demonstração escolhe automaticamente a semana letiva com o dia mais quente de fevereiro-março de 2025 no Rio de Janeiro (17 a 21/02/2025) e
roda o fluxo completo: boletins das 09h com dados <b>reais</b>, leituras internas <b>simuladas</b> a cada 10 min em três ambientes, ingestão no banco e alertas.</p>
{t_demo}
<p>O boletim das 09h acertou a faixa da tarde em <b>{acertos_demo} de {len(prev_demo)} dias</b> dessa semana, incluindo o único dia de <i>Perigo</i> (18/02).
Em três dias, o aviso preventivo de Perigo foi emitido e a tarde ficou em <i>Cautela extrema</i>, o comportamento conservador esperado.</p>
{t_amb}
<p>Foram {fmt(n_leituras)} leituras gravadas, 2 linhas propositalmente corrompidas rejeitadas com o motivo registrado (JSON truncado e temperatura de 85 °C),
{n_alertas.get('tempo_real', 0)} alertas em tempo real e {n_alertas.get('previsao', 0)} alertas de previsão. Pela hipótese de simulação, a sala do 2º andar
sob telhado de fibrocimento acumula mais tempo em <i>Perigo</i>, e o painel indica a sala térrea como destino para remanejar turmas.</p>
{fig('app_boletim.png', 'Figura 10 — Painel Brisa: boletim das 09h de 18/02/2025 (Rio de Janeiro). Previsto 39,5 °C (Perigo); observado 39,8 °C.', '100%')}
{fig('app_salas.png', 'Figura 11 — Painel Brisa: ambientes da escola fictícia (leituras SIMULADAS) e resumo vindo do SQLite.', '100%')}

<h2>3.4 Testes e evidências</h2>
<p>A suíte <code>tests/test_brisa.py</code> tem <b>{n_testes} casos, todos aprovados</b>. Ela cobre: conferência do índice com a tabela do NWS; limites das faixas;
entradas inválidas; limpeza (duplicatas, valores impossíveis, interpolação); ausência de vazamento no dataset de ML; regras de alerta; validação das linhas do
ESP32; ingestão com deduplicação e rejeição; regras <code>CHECK</code> do banco; previsões válidas; superioridade do modelo sobre a linha de base; e
<b>equivalência entre a fórmula em C++ do ESP32 (compilada no teste) e a versão em Python</b>.</p>
<p><b>Bugs encontrados pelos testes:</b> o teste de integridade do banco falhou na primeira execução porque <code>INSERT OR IGNORE</code> descartava em silêncio
leituras impossíveis e as contava como "duplicadas". A correção está no Código 5. <b>Segundo bug</b>, encontrado ao ingerir a saída real do firmware no Wokwi: o horário era gravado só até os minutos, e leituras feitas a cada 2 segundos viravam duplicatas (10 de 11). Passamos a gravar com segundos e criamos um teste de regressão que ingere a saída real do ESP32.</p>
<p class="ev">Trecho de docs/evidencia_testes.txt:</p>
<pre class="ev">{e(chr(10).join(testes.strip().splitlines()[-12:]))}</pre>
<p class="ev">Trecho de docs/evidencia_execucao_pipeline.txt (python src/main.py tudo):</p>
<pre class="ev">{e(chr(10).join(pipeline.strip().splitlines()[-16:]))}</pre>
<p>O menu de terminal também foi executado com entradas roteirizadas, inclusive inválidas (texto no lugar de número, sábado como dia letivo); a saída está em
<code>docs/evidencia_menu_cli.txt</code>.</p>
""")

# ---------------- 4 Conclusões
H.append(f"""
<h1>4 Conclusões</h1>
<h2>4.1 Síntese</h2>
<p>O Brisa mostra que é possível, com dados abertos, Python e componentes de baixo custo, levar à escola uma informação que hoje não chega: <b>quando</b> e
<b>onde</b> o calor vai ficar perigoso e <b>o que fazer</b>. Os dados reais confirmam a dimensão do problema: em três das cinco capitais analisadas, de 45% a
61% das horas de aula ocorrem em <i>Cautela extrema</i> ou pior. Os modelos mostram que a previsão às 09h é útil: o erro médio do pico foi de {fmt(rf_reg['MAE'])} °C e
a acurácia da faixa, de {pct(rf_clf['acuracia'])}, ambos melhores que a persistência. O protótipo integra programação, estatística, ML, banco de dados e IoT num
fluxo coerente, testado e documentado.</p>
<h2>4.2 Limitações</h2>
<ul>
<li><b>Dados externos em grade:</b> a ERA5 (9 a 25 km) suaviza extremos locais. O modelo prevê o calor <i>externo</i>, e o interno depende do prédio.</li>
<li><b>Leituras internas simuladas:</b> o aquecimento por ambiente é uma hipótese não calibrada. Um piloto precisa de medições reais para ajustá-lo.</li>
<li><b>Hardware:</b> o firmware foi executado e validado no simulador Wokwi, mas ainda não numa placa física com sensor real.</li>
<li><b>Classe Perigo:</b> rara (2,9% dos dias de teste). O aviso preventivo troca precisão ({pct(ap['precisao_teste'])}) por recall ({pct(ap['recall_teste'])}).</li>
<li><b>Índice do NWS:</b> foi calibrado para adultos, à sombra e com vento fraco. Ao sol, o estresse pode ser maior, e crianças podem ser mais sensíveis.</li>
<li><b>Calendário:</b> feriados e férias não foram excluídos do "horário escolar".</li>
<li><b>Recomendações:</b> são sugestões operacionais de um protótipo e não substituem orientação de saúde nem protocolos oficiais da rede.</li>
</ul>
<h2>4.3 Medição de impacto</h2>
<p>Propomos um piloto de um semestre em 5 a 10 escolas, comparando o mesmo período do ano anterior (antes) com o uso do Brisa (depois), com os indicadores abaixo.
São <b>resultados esperados</b>, ainda não medidos.</p>
{tab_kpi}
<h2>4.4 Próximos passos</h2>
<ol>
<li>Instalar sensores reais em escolas parceiras e recalibrar o modelo com o aquecimento interno medido.</li>
<li>Usar a previsão horária da Open-Meteo para avisar <i>na véspera</i>, além do boletim das 09h.</li>
<li>Enviar alertas por WhatsApp ou SMS à coordenação e incluir um botão "ação tomada" para medir a adesão.</li>
<li>Incorporar o índice WBGT (temperatura de globo e bulbo úmido), mais adequado a atividades físicas ao sol.</li>
<li>Ranking de escolas por minutos em risco para apoiar a priorização de reformas pela secretaria.</li>
</ol>

<h1>Referências</h1>
<div class="refs">{''.join(f'<p>{r}</p>' for r in REFS)}</div>

<h1>Apêndice A — Como executar</h1>
<p>Repositório: {e(equipe['link_github'])} (pasta <code>1TIAO/GLOBAL-SOLUTION-1</code>). Requisitos: Python 3.10 ou superior.</p>
<pre>python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python src/main.py tudo            # preparar + analisar + treinar + demonstração (~30 s)
streamlit run src/app.py           # painel web em http://localhost:8501
python src/main.py menu            # menu de terminal
python src/main.py boletim --cidade teresina --data 2024-10-08
python -m pytest -v                # testes automatizados</pre>
<p><b>ESP32 (Wokwi):</b> novo projeto ESP32 em wokwi.com; colar <code>src/esp32/sketch.ino</code>, criar <code>brisa_ic.h</code>, substituir o
<code>diagram.json</code> e adicionar a biblioteca <i>DHT sensor library for ESPx</i>. As linhas JSON do Serial Monitor podem ser salvas num <code>.jsonl</code>
e importadas pela opção 3 do menu.</p>
<p><b>Vídeo demonstrativo:</b> {e(equipe['link_video'])}</p>
<p><b>Repositório GitHub (privado, compartilhado com a conta fiap-tutoria):</b> {e(equipe['link_github'])}</p>

<h1>Apêndice B — Checklist dos requisitos da FIAP</h1>
<table><caption>Tabela 12 — Onde cada requisito do enunciado é atendido</caption>
<thead><tr><th>Requisito do enunciado</th><th>Onde está</th></tr></thead><tbody>
<tr><td>Problema real CitizenTech, público-alvo e justificativa baseada em informações</td><td>Seções 1.1 a 1.3 e 2.2 (fontes UNICEF, PLOS ONE, INPE, INMET)</td></tr>
<tr><td>Programa funcional em Python com os conceitos de programação</td><td>Seção 2.11, Códigos 1 a 9; <code>src/brisa/</code>, <code>src/main.py</code>, <code>src/app.py</code></td></tr>
<tr><td>Coleta, tratamento e análise de dados, com tabela, indicador ou gráfico</td><td>Seções 2.5, 2.7 e 3.1 (Tabelas 4 a 6, Figuras 2 a 6); notebook</td></tr>
<tr><td>Dados reais ou base de demonstração identificada, com origem e limitações</td><td>Seção 2.5 (quadro de dados simulados) e <code>data/README.md</code></td></tr>
<tr><td>Conceitos adicionais: estatística, classificação, regressão, banco de dados, sensores</td><td>Seções 2.7 a 2.10 e 3.2; Tabela 2 (integração entre disciplinas)</td></tr>
<tr><td>Evidência de testes e limitações do protótipo</td><td>Seções 3.3, 3.4 e 4.2; <code>docs/evidencia_*.txt</code>, <code>docs/evidencia_wokwi_*</code></td></tr>
<tr><td>Vídeo demonstrativo de até 5 minutos</td><td>4min17s, com legendas: link na capa e no Apêndice A</td></tr>
<tr><td>Nomes completos dos integrantes e turma na primeira página</td><td>Capa</td></tr>
<tr><td>Estrutura mínima: Introdução, Desenvolvimento, Resultados e Conclusões</td><td>Capítulos 1 a 4</td></tr>
<tr><td>Problema, público, objetivo, funcionamento e justificativa das tecnologias</td><td>Seções 1.2 a 1.4, 2.3, 2.4 e 2.6 a 2.11</td></tr>
<tr><td>Origem dos dados, tratamento, explicação dos códigos e evidências dos testes</td><td>Seções 2.5 a 2.10 e 3.4</td></tr>
<tr><td>Imagens, gráficos, tabelas, diagramas e registros do protótipo</td><td>Figuras 1 a 11; Tabelas 1 a 11</td></tr>
<tr><td>ODS relacionados e como medir o impacto</td><td>Seção 1.5 (Tabela 3) e Seção 4.3 (Tabela 9)</td></tr>
<tr><td>Link do vídeo e do repositório GitHub privado (compartilhado com fiap-tutoria)</td><td>Capa e Apêndice A</td></tr>
<tr><td>Códigos em texto legível, não em captura de tela</td><td>Todos os códigos do relatório estão em texto</td></tr>
<tr><td>Estrutura do repositório conforme o template FIAP-PORTFOLIO-AI, com README e integrantes</td><td><code>1TIAO/GLOBAL-SOLUTION-1/README.md</code></td></tr>
<tr><td>Bases simuladas e resultados esperados identificados como tais</td><td>Seções 2.5, 3.3 e 4.3; painel e vídeo</td></tr>
</tbody></table>
</body></html>
""")

saida_html = DOCS / "relatorio_brisa.html"
saida_html.write_text("".join(H), encoding="utf-8")
print(f"HTML: {saida_html}")

chrome = next((c for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "",
                           r"C:\Program Files\Google\Chrome\Application\chrome.exe"] if c and Path(c).exists()), None)
if not chrome:
    sys.exit("Chrome não encontrado: abra o HTML no navegador e use Imprimir > Salvar como PDF.")
pdf = DOCS / "Brisa_GS2026-2_Relatorio.pdf"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", saida_html.as_uri()], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"PDF:  {pdf}")
