"""Banco de dados relacional (SQLite) do Brisa: escolas, ambientes, leituras e alertas."""
import sqlite3
from contextlib import contextmanager

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS escolas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL UNIQUE,
    cidade      TEXT NOT NULL,
    simulada    INTEGER NOT NULL DEFAULT 1   -- 1 = cadastro fictício de demonstração
);
CREATE TABLE IF NOT EXISTS ambientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    escola_id   INTEGER NOT NULL REFERENCES escolas(id),
    nome        TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('sala', 'quadra', 'refeitorio', 'externo')),
    dispositivo TEXT NOT NULL UNIQUE           -- identificador do ESP32
);
CREATE TABLE IF NOT EXISTS leituras (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ambiente_id  INTEGER NOT NULL REFERENCES ambientes(id),
    data_hora    TEXT NOT NULL,
    temperatura  REAL NOT NULL CHECK (temperatura BETWEEN -10 AND 60),
    umidade      REAL NOT NULL CHECK (umidade BETWEEN 0 AND 100),
    indice_calor REAL NOT NULL,
    categoria    TEXT NOT NULL,
    origem       TEXT NOT NULL CHECK (origem IN ('simulado', 'esp32', 'manual')),
    UNIQUE (ambiente_id, data_hora)
);
CREATE TABLE IF NOT EXISTS alertas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ambiente_id  INTEGER REFERENCES ambientes(id),
    escola_id    INTEGER NOT NULL REFERENCES escolas(id),
    data_hora    TEXT NOT NULL,
    tipo         TEXT NOT NULL CHECK (tipo IN ('tempo_real', 'previsao')),
    categoria    TEXT NOT NULL,
    indice_calor REAL,
    mensagem     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS previsoes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    escola_id        INTEGER NOT NULL REFERENCES escolas(id),
    data             TEXT NOT NULL,
    pico_previsto    REAL NOT NULL,
    faixa_prevista   TEXT NOT NULL,
    prob_perigo      REAL,
    pico_observado   REAL,
    faixa_observada  TEXT,
    UNIQUE (escola_id, data)
);
CREATE INDEX IF NOT EXISTS ix_leituras_amb_data ON leituras (ambiente_id, data_hora);
"""


@contextmanager
def conectar(caminho=None):
    con = sqlite3.connect(caminho or config.CAMINHO_BANCO)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def criar_banco(caminho=None):
    with conectar(caminho) as con:
        con.executescript(ESQUEMA)


def inserir_escola(con, nome, cidade, simulada=True) -> int:
    con.execute("INSERT OR IGNORE INTO escolas (nome, cidade, simulada) VALUES (?, ?, ?)",
                (nome, cidade, int(simulada)))
    return con.execute("SELECT id FROM escolas WHERE nome = ?", (nome,)).fetchone()["id"]


def inserir_ambiente(con, escola_id, nome, tipo, dispositivo) -> int:
    con.execute("INSERT OR IGNORE INTO ambientes (escola_id, nome, tipo, dispositivo) "
                "VALUES (?, ?, ?, ?)", (escola_id, nome, tipo, dispositivo))
    return con.execute("SELECT id FROM ambientes WHERE dispositivo = ?",
                       (dispositivo,)).fetchone()["id"]


def ambiente_por_dispositivo(con, dispositivo):
    return con.execute("SELECT a.*, e.cidade FROM ambientes a JOIN escolas e ON e.id = a.escola_id "
                       "WHERE dispositivo = ?", (dispositivo,)).fetchone()


def inserir_leitura(con, ambiente_id, data_hora, temp, umid, ic, cat, origem) -> bool:
    """Grava a leitura. Retorna False se já existir (duplicata).

    Não usa INSERT OR IGNORE porque, no SQLite, ele também ignoraria em silêncio
    violações das regras CHECK; aqui só a duplicidade é tolerada.
    """
    try:
        con.execute(
            "INSERT INTO leituras (ambiente_id, data_hora, temperatura, umidade, "
            "indice_calor, categoria, origem) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ambiente_id, data_hora, temp, umid, ic, cat, origem))
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            return False
        raise
    return True


def inserir_alerta(con, escola_id, ambiente_id, data_hora, tipo, categoria, ic, mensagem):
    con.execute("INSERT INTO alertas (escola_id, ambiente_id, data_hora, tipo, categoria, "
                "indice_calor, mensagem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (escola_id, ambiente_id, data_hora, tipo, categoria, ic, mensagem))


def salvar_previsao(con, escola_id, data, pico, faixa, prob_perigo, pico_obs=None, faixa_obs=None):
    con.execute("INSERT OR REPLACE INTO previsoes (escola_id, data, pico_previsto, faixa_prevista, "
                "prob_perigo, pico_observado, faixa_observada) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (escola_id, data, pico, faixa, prob_perigo, pico_obs, faixa_obs))


# ------------------------------------------------------------ consultas
def resumo_ambientes(con, data=None):
    """Indicadores por ambiente: pico, média e minutos em alerta (leituras de 10 min)."""
    filtro, params = "", ()
    if data:
        filtro, params = "WHERE substr(l.data_hora, 1, 10) = ?", (data,)
    return con.execute(f"""
        SELECT a.nome AS ambiente, a.tipo,
               COUNT(*) AS leituras,
               ROUND(AVG(l.indice_calor), 1) AS ic_medio,
               ROUND(MAX(l.indice_calor), 1) AS ic_maximo,
               SUM(CASE WHEN l.indice_calor >= {config.LIMIAR_ALERTA} THEN 10 ELSE 0 END) AS minutos_em_alerta
        FROM leituras l JOIN ambientes a ON a.id = l.ambiente_id
        {filtro}
        GROUP BY a.id ORDER BY ic_maximo DESC""", params).fetchall()


def alertas_recentes(con, limite=20):
    return con.execute("""
        SELECT al.data_hora, COALESCE(a.nome, 'Escola toda') AS ambiente, al.tipo,
               al.categoria, al.indice_calor, al.mensagem
        FROM alertas al LEFT JOIN ambientes a ON a.id = al.ambiente_id
        ORDER BY al.data_hora DESC, al.id DESC LIMIT ?""", (limite,)).fetchall()


def leituras_do_dia(con, data):
    return con.execute("""
        SELECT a.nome AS ambiente, l.data_hora, l.temperatura, l.umidade, l.indice_calor, l.categoria
        FROM leituras l JOIN ambientes a ON a.id = l.ambiente_id
        WHERE substr(l.data_hora, 1, 10) = ? ORDER BY l.data_hora""", (data,)).fetchall()


def datas_disponiveis(con):
    return [r[0] for r in con.execute(
        "SELECT DISTINCT substr(data_hora, 1, 10) FROM leituras ORDER BY 1")]
