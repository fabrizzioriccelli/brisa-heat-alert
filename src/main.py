"""Ponto de entrada do Brisa.

Uso:
    python src/main.py tudo        # executa o pipeline completo (exceto download)
    python src/main.py baixar      # baixa os dados reais da Open-Meteo (opcional; já versionados)
    python src/main.py preparar    # limpeza + índice de calor + dataset diário
    python src/main.py analisar    # estatísticas e gráficos (docs/img)
    python src/main.py treinar     # treina e avalia os modelos de ML
    python src/main.py demo        # escola demo: sensores simulados + banco + previsões
    python src/main.py boletim --cidade rio_de_janeiro --data 2025-02-17
    python src/main.py menu        # menu interativo
"""
import argparse
import json
import sys
import time

import pandas as pd

from brisa import analise, cli, config, dados, modelo, servicos

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 12)


def etapa(titulo):
    print(f"\n=== {titulo} ===")


def cmd_preparar():
    etapa("Preparação dos dados reais")
    rel = dados.preparar()
    print(json.dumps(rel, ensure_ascii=False, indent=2))
    d = dados.montar_dataset_diario(dados.carregar_horario())
    print(f"Dataset diário: {len(d)} dias úteis x {d.shape[1]} colunas → {config.ARQ_DIARIO.name}")


def cmd_analisar():
    etapa("Análise exploratória e estatística")
    r = analise.executar(dados.carregar_horario())
    print("\nEstatísticas do índice de calor em horário escolar (°C):")
    print(r["descritivas"])
    print("\nHoras de aula por ano com IC ≥ 32,2 °C:")
    print(r["horas"])
    print("\nComparação 2020-2022 x 2023-2025 (pico diário, teste t de Welch):")
    print(r["periodos"])
    print("\nValidação do cálculo:", r["validacao"])
    print(f"Figuras salvas em {config.DIR_FIGURAS.relative_to(config.RAIZ)}/")


def cmd_treinar():
    etapa("Treinamento e avaliação dos modelos")
    r = modelo.treinar_e_avaliar(servicos.carregar_diario())
    print(f"Treino: {r['n_treino']} dias ({r['periodo_treino']}) | Teste: {r['n_teste']} dias ({r['periodo_teste']})")
    print("\nRegressão do pico da tarde:")
    print(pd.DataFrame(r["regressao"]).to_string(index=False))
    print("\nClassificação da faixa de risco:")
    print(pd.DataFrame(r["classificacao"]).to_string(index=False))
    print("\nAlerta de Perigo (limiar calibrado):", r.get("alerta_perigo"))


def cmd_demo():
    etapa("Escola demonstração — sensores simulados, banco SQLite e boletins")
    r = servicos.montar_demo()
    s = r["ingestao"]
    print(f"Semana simulada: {r['dias'][0]} a {r['dias'][-1]} | arquivo: {r['arquivo']}")
    print(f"Leituras: recebidas {s['recebidas']}, gravadas {s['gravadas']}, "
          f"rejeitadas {s['rejeitadas']}, alertas em tempo real {s['alertas']}")
    for e in s["erros"]:
        print("  rejeitada →", e)
    print("\nBoletins das 09h (previsão x observado):")
    for b in r["boletins"]:
        print(f"  {b['data']}: previsto {b['pico_previsto']:.1f} °C ({b['faixa_final']}{' + aviso de Perigo' if b['aviso_perigo'] else ''}) | "
              f"observado {b['pico_observado']:.1f} °C ({b['faixa_observada']})")


def cmd_boletim(cidade, data):
    b = servicos.boletim_do_dia(cidade, data)
    print(json.dumps(b, ensure_ascii=False, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description="Brisa — calor seguro na escola")
    p.add_argument("comando", choices=["baixar", "preparar", "analisar", "treinar", "demo",
                                       "boletim", "menu", "tudo"])
    p.add_argument("--cidade", default="rio_de_janeiro", choices=list(config.CIDADES))
    p.add_argument("--data", default="2025-02-17")
    a = p.parse_args(argv)
    inicio = time.time()
    try:
        if a.comando == "baixar":
            dados.baixar_dados(forcar=True)
        elif a.comando == "preparar":
            cmd_preparar()
        elif a.comando == "analisar":
            cmd_analisar()
        elif a.comando == "treinar":
            cmd_treinar()
        elif a.comando == "demo":
            cmd_demo()
        elif a.comando == "boletim":
            cmd_boletim(a.cidade, a.data)
        elif a.comando == "menu":
            cli.menu()
        elif a.comando == "tudo":
            cmd_preparar(); cmd_analisar(); cmd_treinar(); cmd_demo()
    except (FileNotFoundError, ValueError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    if a.comando != "menu":
        print(f"\nConcluído em {time.time() - inicio:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
