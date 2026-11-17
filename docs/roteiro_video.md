# 🎬 Vídeo demonstrativo: Brisa

O vídeo pronto (**4min00s**, 1080p) é o arquivo `Brisa_GS2026-2_Video.mp4`, gerado fora do repositório pelos scripts da pasta `video/` da sessão.
A narração usa vozes neurais pt-BR (Microsoft Edge TTS: Francisca e Antonio). As imagens vêm de slides gerados a partir dos resultados reais, de gravações do painel e do firmware rodando no simulador Wokwi.

**Publicação:** suba o arquivo no YouTube como **"Não listado"**, cole o link em `docs/equipe.json` (`link_video`) e no `README.md`, e rode `python docs/gerar_relatorio.py`.

| # | Tela | Voz | Narração |
|---|---|---|---|
| 1 | Capa com QUERO CONCORRER e integrantes → README.md | Francisca (feminina) | Quero concorrer! Olá, nós somos Bruna, Fábio, Fabrizzio, Gabriel e Natasha, e este é o Brisa: calor seguro na escola. |
| 2 | Slide: dados do problema (UNICEF, PLOS ONE, INPE) | Antonio (masculina) | O calor extremo já está tirando crianças da sala de aula. Em 2024, segundo o UNICEF, as ondas de calor foram o evento climático que mais afetou a escolarização no mundo: cerca de cento e setenta e um milhões de estudantes. E, no Brasil, um estudo publicado na PLOS ONE estimou mais de quarenta e oito mil mortes ligadas a ondas de calor entre 2000 e 2018. |
| 3 | Slide: a lacuna das soluções atuais | Francisca (feminina) | Os alertas que existem hoje falam da cidade, não da sala de aula. A coordenadora não sabe qual sala vai ficar perigosa, nem a que horas, nem o que fazer. E, na prática, só reage quando alguém passa mal. |
| 4 | Slide: arquitetura | Antonio (masculina) | O Brisa resolve isso em três camadas. Às nove da manhã, um modelo de inteligência artificial prevê o pico de calor da tarde. Durante o dia, sensores com ESP32 medem cada sala e avisam no próprio ambiente. E um backend em Python, com banco SQLite, valida as leituras, gera alertas e mostra tudo num painel. |
| 5 | Slide: gráficos com dados reais | Francisca (feminina) | Começamos pelos dados reais: seis anos de medições horárias, de 2020 a 2025, em cinco capitais. São duzentos e sessenta e três mil registros. Em Teresina, sessenta e um por cento das horas de aula ficam em cautela extrema ou pior. Em Manaus, metade. E o pico diário subiu mais de um grau entre os dois triênios, com teste estatístico significativo. |
| 6 | Gravação do painel: boletim das 09h (Rio, 18/02/2025) | Antonio (masculina) | Este é o boletim das nove horas. No dia dezoito de fevereiro de 2025, no Rio de Janeiro, o Brisa previu um pico de trinta e nove e meio graus: faixa de perigo. O pico real foi de trinta e nove vírgula oito. E o painel já diz o que fazer: suspender a educação física, remanejar as turmas e avisar as famílias. |
| 7 | Slide: métricas dos modelos + matriz de confusão | Francisca (feminina) | Para chegar nisso, treinamos com 2020 a 2023 e testamos com 2024 e 2025, que o modelo nunca viu. O Random Forest erra o pico, em média, um vírgula três grau, e acerta a faixa de risco em oitenta e quatro por cento dos dias, superando a linha de base. Como o perigo é raro, calibramos um aviso preventivo que identifica oitenta e sete por cento desses dias. |
| 8 | Gravação do firmware real rodando no Wokwi (LEDs verde → amarelo → vermelho) | Antonio (masculina) | Agora, o sensor na sala. Este é o firmware real rodando no simulador Wokwi: um ESP32 com sensor DHT22. Ele calcula o índice de calor no próprio chip, então funciona mesmo sem internet. Conforme a temperatura sobe, o LED muda de verde para amarelo e depois para vermelho, com alerta sonoro. E cada leitura sai em formato JSON para o backend. |
| 9 | Gravação do painel: salas + terminal da demonstração | Francisca (feminina) | No backend, cada linha é validada antes de entrar no banco. Leituras corrompidas são rejeitadas com o motivo registrado. Nesta demonstração, com uma escola fictícia e leituras simuladas a partir do clima real, a sala do segundo andar passa mais tempo em perigo, e o Brisa indica a sala térrea para receber as turmas. |
| 10 | Terminal: pytest com 32 testes passando | Antonio (masculina) | São trinta e dois testes automatizados, todos passando. Um deles compila o código C mais mais do ESP32 e confere se ele calcula exatamente o mesmo que o Python. E os testes ainda encontraram dois bugs reais no armazenamento das leituras, que nós corrigimos. |
| 11 | Slide: disciplinas e ODS | Francisca (feminina) | O projeto integra programação em Python, estatística, análise de dados com Pandas e Seaborn, machine learning, banco de dados e internet das coisas. E contribui com os Objetivos de Desenvolvimento Sustentável três, quatro, onze e treze. |
| 12 | Slide: impacto, limitações e encerramento | Antonio (masculina) | Para medir o impacto, propomos acompanhar as horas de aula em risco por sala e a antecedência dos avisos num piloto real. Sabemos das limitações: os dados externos são em grade, e as leituras internas da demonstração são simuladas. O próximo passo é instalar sensores de verdade. Brisa: menos calor, mais aula. Obrigado! |

## Checklist
- [x] "QUERO CONCORRER" nos primeiros segundos, com integrantes e README
- [x] Integração entre disciplinas (cena 11)
- [x] Demonstração prática: painel, firmware no Wokwi, terminal e testes
- [x] Duração ≤ 5 min (4:00)
- [x] Dados simulados chamados de simulados na narração
- [ ] Publicar no YouTube como "Não listado" e colocar o link no PDF e no README
