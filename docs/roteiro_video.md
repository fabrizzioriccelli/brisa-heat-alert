# 🎬 Vídeo demonstrativo: Brisa

Vídeo final: **4min24s**, 1080p, 30 fps.
- **Narração:** uma única voz, gerada no ElevenLabs a partir do texto abaixo.
- **Cenas animadas:** HTML/CSS renderizado quadro a quadro, sincronizado com cada palavra da narração. A sincronia vem dos timestamps do reconhecimento de fala (Vosk).
- **Acabamento:** legendas embutidas, título de capítulo, barra de progresso, abertura e encerramento com a marca.
- **Legendas avulsas:** em `docs/legendas_video.srt`, para enviar ao YouTube.

O projeto **não concorre ao pódio**, por isso o vídeo não tem a frase "QUERO CONCORRER".

**Publicação:** suba o vídeo no YouTube como **"Não listado"**, cole o link em `docs/equipe.json` (`link_video`) e no `README.md`, e rode `python docs/gerar_relatorio.py`.

| Início | Cena | Tela | Narração |
|---|---|---|---|
| 0:00 | Abertura da marca | Logo animado (sem narração) | — |
| 0:03 | Abertura | Abertura animada: título e equipe | Olá! Nós somos Bruna, Fábio, Fabrizzio, Gabriel e Natasha, e este é o Brisa: calor seguro na escola. |
| 0:11 | O problema | Três números do problema, com contagem animada (UNICEF, PLOS ONE, INPE) | O calor extremo já está tirando crianças da sala de aula. Em 2024, segundo o UNICEF, as ondas de calor foram o evento climático que mais afetou a escolarização no mundo: cerca de 171 milhões de estudantes. No Brasil, um estudo publicado na PLOS ONE estimou mais de 48 mil mortes ligadas a ondas de calor entre 2000 e 2018. |
| 0:38 | A lacuna | Comparação: como é hoje × o que a coordenação precisa | Os alertas que existem hoje falam da cidade, não da sala de aula. A coordenadora não sabe qual sala vai ficar perigosa, nem a que horas, nem o que fazer. E, na prática, só reage quando alguém passa mal. |
| 0:51 | A solução | As três camadas da solução | O Brisa resolve isso em três camadas. Às 9h, um modelo de inteligência artificial prevê o pico de calor da tarde. Durante o dia, sensores com ESP32 medem cada sala e avisam no próprio ambiente. E um backend em Python, com banco SQLite, valida as leituras, gera alertas e mostra tudo num painel. |
| 1:14 | Dados reais | 263.040 registros e barras por cidade | Começamos pelos dados reais: seis anos de medições, hora a hora, de 2020 a 2025, em cinco capitais. São 263 mil registros. Em Teresina, 61% das horas de aula ficam em cautela extrema ou pior. Em Manaus, metade. E o pico diário subiu mais de 1 °C entre os dois triênios, com teste estatístico significativo. |
| 1:41 | Demonstração · boletim das 9h | Gravação do painel: boletim das 9h + painel com pico previsto e real | Este é o boletim das 9h. Em 18 de fevereiro de 2025, no Rio de Janeiro, o Brisa previu um pico de 39,5 °C: faixa de perigo. O pico real foi de 39,8 °C. E o painel já diz o que fazer: suspender a educação física, remanejar as turmas e avisar as famílias. |
| 2:03 | Machine Learning | Linha do tempo treino/teste e barras de desempenho | Para chegar nisso, treinamos o modelo com os dados de 2020 a 2023 e testamos com 2024 e 2025, anos que ele nunca viu. O Random Forest erra o pico, em média, em 1,3 °C, e acerta a faixa de risco em 84% dos dias, superando a linha de base. Como o perigo é raro, calibramos um aviso preventivo que identifica 87% desses dias. |
| 2:30 | Demonstração · ESP32 | Gravação do firmware no Wokwi + legenda dos LEDs sincronizada | Agora, o sensor na sala. Este é o firmware real rodando no simulador Wokwi: um ESP32 com sensor DHT22. Ele calcula o índice de calor no próprio chip, então funciona mesmo sem internet. Conforme a temperatura sobe, o LED muda de verde para amarelo e depois para vermelho, com alerta sonoro. E cada leitura é enviada em JSON para o backend. |
| 2:57 | Demonstração · salas e banco | Gravação do painel de salas → terminal da demonstração | No backend, cada leitura é validada antes de entrar no banco. Leituras corrompidas são rejeitadas, e o motivo fica registrado. Nesta demonstração, com uma escola fictícia e leituras simuladas a partir do clima real, a sala do 2º andar passa mais tempo em perigo, e o Brisa indica a sala térrea para receber as turmas. |
| 3:19 | Testes | Terminal com os 32 testes + destaques | São 32 testes automatizados, todos passando. Um deles compila o código C++ do ESP32 e confere se ele calcula exatamente o mesmo que o Python. E os testes ainda encontraram dois bugs reais no armazenamento das leituras, que nós corrigimos. |
| 3:38 | Disciplinas e ODS | Disciplinas e ODS | O projeto integra programação em Python, estatística, análise de dados com Pandas e Seaborn, aprendizado de máquina, banco de dados e internet das coisas. E contribui com os ODS 3, 4, 11 e 13. |
| 3:56 | Impacto e próximos passos | Impacto, limitações e encerramento | Para medir o impacto, propomos acompanhar, num piloto real, as horas de aula em risco em cada sala e a antecedência dos avisos. Sabemos das limitações: os dados externos têm baixa resolução, e as leituras internas da demonstração são simuladas. O próximo passo é instalar sensores de verdade. Brisa: menos calor, mais aula. Obrigado! |
| 4:19 | Encerramento | Logo, equipe e repositório | — |

## Checklist
- [x] Integrantes nos primeiros segundos
- [x] Integração entre disciplinas (cena 11)
- [x] Demonstração prática: painel, firmware no Wokwi, terminal e testes
- [x] Duração ≤ 5 min (4:24)
- [x] Dados simulados chamados de simulados na narração e na tela
- [ ] Publicar no YouTube como "Não listado" e colocar o link no PDF e no README
