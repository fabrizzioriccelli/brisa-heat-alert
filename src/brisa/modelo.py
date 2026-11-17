"""Modelos de Machine Learning do Brisa.

Pergunta respondida às 09h de cada dia letivo:
  "Qual será o pico do índice de calor entre 12h e 17h e em que faixa de risco?"

* Regressão  -> valor do pico (°C)
* Classificação -> categoria do pico (Normal, Cautela, Cautela extrema, Perigo)

Divisão temporal: treino 2020-2023, teste 2024-2025 (simula uso no futuro).
"""
import json

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, mean_absolute_error, mean_squared_error, r2_score,
                             recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from . import config
from .indice_calor import classificar

ATRIBUTOS = [
    "temp_09h", "umidade_09h", "ic_09h", "temp_06h", "aquecimento_manha",
    "radiacao_manha", "vento_09h", "ic_max_tarde_ontem", "mes_sen", "mes_cos",
]
CLASSES = ["Normal", "Cautela", "Cautela extrema", "Perigo"]
ANO_CORTE = 2024
PRECISAO_MINIMA = 0.35


def _agrupar_categoria(cat: str) -> str:
    # "Perigo extremo" não ocorre na base; se ocorrer, é tratado como "Perigo"
    return "Perigo" if cat == "Perigo extremo" else cat


def dividir(d: pd.DataFrame):
    d = d.copy()
    d["data"] = pd.to_datetime(d["data"])
    d["categoria_tarde"] = d["ic_max_tarde"].apply(classificar).apply(_agrupar_categoria)
    treino = d[d["data"].dt.year < ANO_CORTE]
    teste = d[d["data"].dt.year >= ANO_CORTE]
    return treino, teste


def _salvar_fig(nome):
    config.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(config.DIR_FIGURAS / nome, dpi=150)
    plt.close()


def treinar_e_avaliar(d: pd.DataFrame) -> dict:
    treino, teste = dividir(d)
    Xtr, Xte = treino[ATRIBUTOS], teste[ATRIBUTOS]
    resultados = {"n_treino": len(treino), "n_teste": len(teste),
                  "periodo_treino": "2020-2023", "periodo_teste": "2024-2025"}

    # ---------------- Regressão do pico ----------------
    ytr, yte = treino["ic_max_tarde"], teste["ic_max_tarde"]
    regs = {
        "Linha de base (pico de ontem)": None,
        "Regressão Linear": make_pipeline(StandardScaler(), LinearRegression()),
        "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                               random_state=config.SEMENTE, n_jobs=-1),
    }
    tab_reg, previsoes_reg = [], {}
    for nome, modelo in regs.items():
        if modelo is None:
            prev = teste["ic_max_tarde_ontem"].to_numpy()
        else:
            modelo.fit(Xtr, ytr)
            prev = modelo.predict(Xte)
        previsoes_reg[nome] = prev
        tab_reg.append({
            "modelo": nome,
            "MAE": round(mean_absolute_error(yte, prev), 3),
            "RMSE": round(float(np.sqrt(mean_squared_error(yte, prev))), 3),
            "R2": round(r2_score(yte, prev), 3),
        })
    resultados["regressao"] = tab_reg
    melhor_reg_nome = min(tab_reg[1:], key=lambda r: r["MAE"])["modelo"]
    melhor_reg = regs[melhor_reg_nome]

    # ---------------- Classificação da faixa ----------------
    ctr, cte = treino["categoria_tarde"], teste["categoria_tarde"]
    clfs = {
        "Linha de base (faixa de ontem)": None,
        "Regressão Logística": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
        "Árvore de Decisão": DecisionTreeClassifier(max_depth=6, class_weight="balanced",
                                                     random_state=config.SEMENTE),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                class_weight="balanced_subsample",
                                                random_state=config.SEMENTE, n_jobs=-1),
    }
    tab_clf, previsoes_clf = [], {}
    for nome, modelo in clfs.items():
        if modelo is None:
            prev = teste["ic_max_tarde_ontem"].apply(classificar).apply(_agrupar_categoria).to_numpy()
        else:
            modelo.fit(Xtr, ctr)
            prev = modelo.predict(Xte)
        previsoes_clf[nome] = prev
        rec = recall_score(cte, prev, labels=CLASSES, average=None, zero_division=0)
        tab_clf.append({
            "modelo": nome,
            "acuracia": round(accuracy_score(cte, prev), 3),
            "f1_macro": round(f1_score(cte, prev, average="macro", zero_division=0), 3),
            "recall_cautela_extrema": round(float(rec[2]), 3),
            "recall_perigo": round(float(rec[3]), 3),
        })
    resultados["classificacao"] = tab_clf
    melhor_clf_nome = max(tab_clf[1:], key=lambda r: r["f1_macro"])["modelo"]
    melhor_clf = clfs[melhor_clf_nome]
    resultados["relatorio_melhor_classificador"] = classification_report(
        cte, previsoes_clf[melhor_clf_nome], labels=CLASSES, zero_division=0, output_dict=True)

    # Limiar de segurança para "Perigo": escolhido na VALIDAÇÃO (anos anteriores ->
    # validação 2021-2023) como o de MAIOR recall entre os que mantêm precisão >= 35%
    # (limita alarmes falsos); só depois é medido no teste 2024-2025.
    if hasattr(melhor_clf, "predict_proba"):
        from sklearn.base import clone
        # Validação temporal em janela expansível: 2021, 2022 e 2023, cada ano
        # previsto por um modelo treinado só com os anos anteriores.
        p_val, y_val = [], []
        for ano_val in range(2021, ANO_CORTE):
            sub = treino[treino["data"].dt.year < ano_val]
            val = treino[treino["data"].dt.year == ano_val]
            aux = clone(melhor_clf).fit(sub[ATRIBUTOS], sub["categoria_tarde"])
            if "Perigo" not in aux.classes_:
                continue
            p_val.append(aux.predict_proba(val[ATRIBUTOS])[:, list(aux.classes_).index("Perigo")])
            y_val.append((val["categoria_tarde"] == "Perigo").to_numpy())
        p_val, y_val = np.concatenate(p_val), np.concatenate(y_val)
        melhor_rec, limiar = -1.0, 0.5
        for t in np.arange(0.05, 0.55, 0.05):
            pr = p_val >= t
            tp = (pr & y_val).sum()
            prec = tp / max(pr.sum(), 1); rec = tp / max(y_val.sum(), 1)
            if prec >= PRECISAO_MINIMA and rec > melhor_rec:
                melhor_rec, limiar = rec, round(float(t), 2)
        p_te = melhor_clf.predict_proba(Xte)[:, list(melhor_clf.classes_).index("Perigo")]
        y_te = (cte == "Perigo").to_numpy()
        pr = p_te >= limiar
        tp = int((pr & y_te).sum())
        resultados["alerta_perigo"] = {
            "limiar_probabilidade": limiar,
            "escolhido_em": "validação temporal 2021-2023 (maior recall com precisão >= 35%)",
            "recall_validacao": round(float(melhor_rec), 3),
            "recall_teste": round(float(tp / max(y_te.sum(), 1)), 3),
            "precisao_teste": round(float(tp / max(pr.sum(), 1)), 3),
            "dias_perigo_reais_teste": int(y_te.sum()),
            "alertas_emitidos_teste": int(pr.sum()),
        }

    # Desempenho por cidade (melhor classificador)
    por_cidade = []
    for cidade, g in teste.assign(prev=previsoes_clf[melhor_clf_nome]).groupby("cidade"):
        por_cidade.append({"cidade": config.CIDADES[cidade][0],
                           "acuracia": round(accuracy_score(g["categoria_tarde"], g["prev"]), 3),
                           "dias": len(g)})
    resultados["classificacao_por_cidade"] = por_cidade
    resultados["melhor_regressor"] = melhor_reg_nome
    resultados["melhor_classificador"] = melhor_clf_nome

    # ---------------- Figuras ----------------
    cm = confusion_matrix(cte, previsoes_clf[melhor_clf_nome], labels=CLASSES)
    plt.figure(figsize=(6.4, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd", xticklabels=CLASSES, yticklabels=CLASSES)
    plt.xlabel("Faixa prevista às 09h"); plt.ylabel("Faixa observada (12h-17h)")
    plt.title(f"Matriz de confusão — {melhor_clf_nome} (teste 2024-2025)")
    _salvar_fig("fig_matriz_confusao.png")

    plt.figure(figsize=(6.4, 5))
    prev = previsoes_reg[melhor_reg_nome]
    plt.scatter(yte, prev, s=6, alpha=0.35, color="#F08A24")
    lim = [yte.min() - 1, yte.max() + 1]
    plt.plot(lim, lim, "k--", lw=1, label="previsão perfeita")
    plt.axvline(config.LIMIAR_ALERTA, color="#D63E2F", lw=0.8, ls=":")
    plt.axhline(config.LIMIAR_ALERTA, color="#D63E2F", lw=0.8, ls=":", label="limiar de alerta 32,2 °C")
    plt.xlabel("Pico observado (°C)"); plt.ylabel("Pico previsto (°C)")
    plt.title(f"Regressão do pico da tarde — {melhor_reg_nome}")
    plt.legend(); _salvar_fig("fig_regressao_pico.png")

    if hasattr(melhor_reg, "feature_importances_"):
        imp = pd.Series(melhor_reg.feature_importances_, index=ATRIBUTOS).sort_values()
        plt.figure(figsize=(6.4, 4.4))
        imp.plot.barh(color="#2E7DA6")
        plt.title("Importância dos atributos — Random Forest (regressão)")
        plt.xlabel("Importância relativa")
        _salvar_fig("fig_importancia_atributos.png")
        resultados["importancia_atributos"] = imp.sort_values(ascending=False).round(4).to_dict()

    # ---------------- Persistência ----------------
    config.DIR_MODELOS.mkdir(parents=True, exist_ok=True)
    # Modelos finais são re-treinados com todos os anos para uso no protótipo
    tudo = pd.concat([treino, teste])
    melhor_reg.fit(tudo[ATRIBUTOS], tudo["ic_max_tarde"])
    melhor_clf.fit(tudo[ATRIBUTOS], tudo["categoria_tarde"])
    joblib.dump(melhor_reg, config.DIR_MODELOS / "regressor_pico.joblib", compress=3)
    joblib.dump(melhor_clf, config.DIR_MODELOS / "classificador_faixa.joblib", compress=3)
    with open(config.DIR_MODELOS / "metricas.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    return resultados


def carregar_modelos():
    try:
        reg = joblib.load(config.DIR_MODELOS / "regressor_pico.joblib")
        clf = joblib.load(config.DIR_MODELOS / "classificador_faixa.joblib")
    except FileNotFoundError as e:
        raise FileNotFoundError("Modelos não encontrados. Rode 'python src/main.py treinar'.") from e
    return reg, clf


def _limiar_perigo() -> float:
    try:
        with open(config.DIR_MODELOS / "metricas.json", encoding="utf-8") as f:
            return float(json.load(f)["alerta_perigo"]["limiar_probabilidade"])
    except (FileNotFoundError, KeyError):
        return 0.5


def prever(atributos: dict, modelos=None) -> dict:
    """Previsão para um dia a partir dos atributos da manhã."""
    faltando = [a for a in ATRIBUTOS if a not in atributos]
    if faltando:
        raise ValueError(f"Atributos ausentes: {faltando}")
    reg, clf = modelos or carregar_modelos()
    x = pd.DataFrame([{a: atributos[a] for a in ATRIBUTOS}])
    pico = float(reg.predict(x)[0])
    probs = dict(zip(clf.classes_, clf.predict_proba(x)[0].round(3)))
    limiar = _limiar_perigo()
    return {
        "alerta_perigo": bool(probs.get("Perigo", 0) >= limiar),
        "limiar_perigo": limiar,
        "pico_previsto": round(pico, 1),
        "faixa_prevista": str(clf.predict(x)[0]),
        "faixa_pelo_pico": classificar(pico),
        "probabilidades": {k: float(v) for k, v in probs.items()},
    }
