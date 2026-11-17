# data/

| Pasta / arquivo | Natureza | Descrição |
|---|---|---|
| `raw/openmeteo_<cidade>_2020_2025.csv` | **REAL** | Série horária 01/01/2020–31/12/2025 (temperatura a 2 m, umidade relativa, sensação térmica, vento a 10 m e radiação de onda curta) da API de histórico da Open-Meteo, que usa a reanálise ERA5/ERA5-Land (Copernicus/ECMWF). Baixada em 17/11/2026 com `python src/main.py baixar`. |
| `processed/clima_horario_5_capitais.csv.gz` | Derivado do real | Base limpa + índice de calor, faixa de risco e marcadores de horário escolar (263.040 linhas). |
| `processed/dataset_alerta_diario.csv` | Derivado do real | 1 linha por cidade e dia útil: atributos da manhã (até 09h) e pico da tarde (12h–17h). 7.825 linhas. |
| `processed/resultados_analise.json` | Derivado do real | Tabelas estatísticas usadas no relatório. |
| `simulated/leituras_esp32_simuladas.jsonl` | **SIMULADO** | Leituras internas de 3 ambientes de uma escola **fictícia**, a cada 10 min: clima externo real + aquecimento interno **hipotético**. Inclui 2 linhas corrompidas de propósito para testar a validação. |
| `brisa.db` | Misto | Banco SQLite da demonstração (escola fictícia, leituras simuladas, previsões com dados reais). |

**Limitações:** a ERA5 é uma reanálise em grade (~9–25 km). Ela não captura ilhas de calor de bairro nem o interior das salas, e o horário escolar ignora feriados e férias.
