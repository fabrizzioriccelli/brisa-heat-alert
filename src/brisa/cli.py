"""Menu interativo de terminal do Brisa (para a coordenação escolar)."""
from . import alertas, banco, config, modelo, sensor, servicos
from .indice_calor import classificar, indice_de_calor

LINHA = "-" * 64


def ler_float(msg: str, minimo: float, maximo: float) -> float:
    while True:
        texto = input(msg).strip().replace(",", ".")
        try:
            valor = float(texto)
        except ValueError:
            print("  ! Digite um número válido.")
            continue
        if minimo <= valor <= maximo:
            return valor
        print(f"  ! O valor deve estar entre {minimo} e {maximo}.")


def opcao_calculadora():
    print(LINHA)
    t = ler_float("Temperatura do ambiente (°C): ", -10, 60)
    u = ler_float("Umidade relativa (%): ", 0, 100)
    ic = indice_de_calor(t, u)
    cat = classificar(ic)
    print(f"\n  Índice de calor: {ic:.1f} °C  →  {cat}")
    for r in alertas.recomendacoes(cat):
        print(f"   • {r}")


def opcao_boletim():
    print(LINHA)
    chaves = list(config.CIDADES)
    for i, c in enumerate(chaves, start=1):
        print(f"  {i}. {config.CIDADES[c][0]}")
    idx = int(ler_float("Escolha a cidade: ", 1, len(chaves))) - 1
    data = input("Data (AAAA-MM-DD, dia útil entre 2020-01-02 e 2025-12-31): ").strip()
    try:
        b = servicos.boletim_do_dia(chaves[idx], data)
    except ValueError as e:
        print(f"  ! {e}")
        return
    print(f"\n  BOLETIM DAS 09h — {b['cidade']} — {b['data']}")
    print(f"  Manhã: {b['manha']['temp_09h']:.1f} °C, UR {b['manha']['umidade_09h']:.0f}%, "
          f"IC {b['manha']['ic_09h']:.1f} °C")
    print(f"  Pico previsto (12h-17h): {b['pico_previsto']:.1f} °C  →  {b['faixa_final']}")
    print("  Probabilidades: " + ", ".join(
        f"{k} {b['probabilidades'].get(k, 0):.0%}" for k in modelo.CLASSES))
    for r in b["recomendacoes"]:
        print(f"   • {r}")
    print(f"  [Verificação] Pico real observado: {b['pico_observado']:.1f} °C ({b['faixa_observada']})")


def opcao_ingerir():
    print(LINHA)
    caminho = input("Arquivo .jsonl com leituras do ESP32 "
                    "(Enter = data/simulated/leituras_esp32_simuladas.jsonl): ").strip()
    arq = config.RAIZ / caminho if caminho else config.DIR_SIMULADOS / "leituras_esp32_simuladas.jsonl"
    try:
        linhas = arq.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        print(f"  ! Arquivo não encontrado: {arq}")
        return
    sensor.cadastrar_escola_demo()
    stats = sensor.ingerir(linhas, origem="esp32" if caminho else "simulado")
    print(f"  Recebidas {stats['recebidas']} | gravadas {stats['gravadas']} | "
          f"duplicadas {stats['duplicadas']} | rejeitadas {stats['rejeitadas']} | "
          f"alertas {stats['alertas']}")
    for e in stats["erros"][:5]:
        print(f"   ! {e}")


def opcao_relatorio():
    print(LINHA)
    with banco.conectar() as con:
        datas = banco.datas_disponiveis(con)
        if not datas:
            print("  Banco vazio. Rode 'python src/main.py demo' ou a opção 3.")
            return
        print("  Datas com leituras: " + ", ".join(datas))
        data = input("Data (Enter = todas): ").strip() or None
        print(f"\n  {'Ambiente':46} {'IC méd':>7} {'IC máx':>7} {'min alerta':>10}")
        for r in banco.resumo_ambientes(con, data):
            print(f"  {r['ambiente'][:46]:46} {r['ic_medio']:7.1f} {r['ic_maximo']:7.1f} "
                  f"{r['minutos_em_alerta']:10d}")
        print("\n  Últimos alertas:")
        for a in banco.alertas_recentes(con, 8):
            print(f"   {a['data_hora']}  {a['mensagem'][:90]}")


def menu():
    opcoes = {
        "1": ("Calcular índice de calor de um ambiente", opcao_calculadora),
        "2": ("Boletim das 09h (previsão da tarde com IA)", opcao_boletim),
        "3": ("Importar leituras de sensores (ESP32)", opcao_ingerir),
        "4": ("Relatório dos ambientes da escola", opcao_relatorio),
    }
    while True:
        print(f"\n{LINHA}\n  BRISA — calor seguro na escola\n{LINHA}")
        for k, (texto, _) in opcoes.items():
            print(f"  {k}. {texto}")
        print("  0. Sair")
        escolha = input("Opção: ").strip()
        if escolha == "0":
            print("Até logo!")
            break
        if escolha not in opcoes:
            print("  ! Opção inválida.")
            continue
        try:
            opcoes[escolha][1]()
        except FileNotFoundError as e:
            print(f"  ! {e}")
