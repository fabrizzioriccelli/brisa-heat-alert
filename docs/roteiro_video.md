# 🎬 Roteiro do vídeo: Brisa (máximo de 5 minutos)

**Formato:** gravação de tela (OBS Studio ou o gravador do sistema) em 1080p, com a voz dos integrantes; câmera opcional no canto.
**Publicação:** YouTube, visibilidade **"Não listado"**. Cole o link em `docs/equipe.json`, rode `python docs/gerar_relatorio.py` para atualizar o PDF e coloque o link no `README.md`.
**Tempo-alvo:** 4min45s, deixando folga em relação ao limite.

> Antes de gravar: rode `python src/main.py tudo`, deixe `streamlit run src/app.py` aberto no navegador, o projeto do Wokwi pronto e um terminal na pasta `GLOBAL-SOLUTION-1`.

| Tempo | Quem fala | Na tela | Fala (sugestão) |
|---|---|---|---|
| **0:00–0:12** | Integrante 1 | `README.md` do repositório, com o nome do grupo | "Olá! Somos o grupo **[NOME DO GRUPO]** e **QUERO CONCORRER**. Este é o Brisa: calor seguro na escola." |
| 0:12–0:45 | Integrante 1 | Capa do PDF → seção 1.1 | "Em 2024, ondas de calor foram o evento climático que mais afetou aulas no mundo: cerca de 171 milhões de estudantes, segundo o UNICEF. No Brasil, um estudo na PLOS ONE estimou 48 mil mortes ligadas a ondas de calor entre 2000 e 2018. Mesmo assim, a escola não sabe quanto calor faz dentro de cada sala e só reage quando alguém passa mal." |
| 0:45–1:10 | Integrante 2 | Figura 1 (arquitetura) | "Nossa usuária é a coordenação escolar. O Brisa tem três camadas: um boletim às 9h, feito com IA, que prevê o pico de calor da tarde; sensores ESP32 nas salas; e um backend em Python com banco SQLite e painel web. Tudo usa o índice de calor oficial do serviço meteorológico dos EUA, o NWS/NOAA." |
| 1:10–1:45 | Integrante 2 | Figuras 2 e 4 do PDF (ou a aba Panorama) | "Usamos dados **reais** e horários de 2020 a 2025 de cinco capitais, um total de 263 mil registros. Em Teresina, 61% das horas de aula ficam em 'Cautela extrema' ou pior; em Manaus, metade. E o pico diário médio subiu entre 1 e 1,4 grau em 2023–2025, com teste t significativo, lembrando que o período teve El Niño." |
| 1:45–2:35 | Integrante 3 | **Painel → Boletim das 09h**, Rio de Janeiro, 18/02/2025 | "Às 9h do dia 18 de fevereiro de 2025, o Brisa previu pico de 39,5 graus: faixa de **Perigo**. O pico real foi de 39,8. O painel diz o que fazer: suspender atividade física intensa, remanejar turmas, avisar as famílias. Treinamos com 2020–2023 e testamos com 2024–2025: o Random Forest erra o pico em 1,33 grau, em média, e acerta a faixa em 84% dos dias, melhor que a linha de base. Como 'Perigo' é raro, calibramos um aviso preventivo que pega 87% desses dias." *(mostrar a Tabela 7/8 do PDF por 3 s)* |
| 2:35–3:20 | Integrante 4 | **Wokwi** com o ESP32 rodando | "Este é o nó de sala: ESP32 com DHT22. Ele calcula o índice no próprio chip, então funciona mesmo sem internet." *(clicar no DHT22 e subir a temperatura de 28 para 36 °C com umidade de 60%)* "Vejam: o LED passa de verde para amarelo e depois vermelho, e o buzzer apita. Cada leitura sai como JSON pela serial." *(mostrar o Serial Monitor)* |
| 3:20–3:50 | Integrante 4 | **Painel → Salas em tempo real** + terminal | "O backend valida cada linha, grava no SQLite e gera alertas sem lotar a equipe de notificações. Aqui a escola é fictícia e as leituras são simuladas a partir do clima real: a sala do 2º andar, sob telhado de fibrocimento, passa 2.250 minutos em Perigo na semana, e o Brisa indica a sala térrea para receber as turmas." *(no terminal: `python src/main.py demo` mostrando as 2 linhas rejeitadas)* |
| 3:50–4:10 | Integrante 5 | Terminal: `python -m pytest -v` | "São 30 testes automatizados, todos passando, inclusive um que compila o código C++ do ESP32 e compara com o Python. Os testes ainda acharam um bug real no banco, que corrigimos." |
| 4:10–4:35 | Integrante 5 | Tabela 2 (disciplinas) e Tabela 3 (ODS) | "Integramos Python, estatística, Pandas e Seaborn, Machine Learning, banco de dados e IoT. O projeto contribui para os ODS 3, 4, 11 e 13, e propomos indicadores como horas de aula em risco por sala e antecedência dos avisos para medir o impacto num piloto." |
| 4:35–4:50 | Integrante 1 | Seção 4.2 e depois o logo | "Limitações: o dado externo é em grade e as leituras internas da demo são simuladas. O próximo passo é instalar sensores reais e recalibrar. Brisa: menos calor, mais aula. Obrigado!" |

## Checklist de gravação
- [ ] A frase **"QUERO CONCORRER"** aparece nos primeiros segundos, junto com o nome do grupo.
- [ ] O vídeo mostra a integração entre disciplinas (Tabela 2).
- [ ] Há demonstração prática: painel, ESP32 no Wokwi, terminal e testes.
- [ ] Duração ≤ 5:00 (confira antes de publicar).
- [ ] YouTube em **"Não listado"**, com o link no PDF (`docs/equipe.json` → `python docs/gerar_relatorio.py`) e no `README.md`.
- [ ] Dados simulados chamados de "simulados" na fala.
