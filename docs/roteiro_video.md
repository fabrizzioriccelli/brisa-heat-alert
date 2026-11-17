# 🎬 Vídeo demonstrativo: Brisa

Vídeo pronto: **4min17s**, 1080p (`Brisa_GS2026-2_Video.mp4`), com legendas embutidas, título de capítulo em cada cena e barra de progresso. As legendas também estão em `docs/legendas_video.srt`, para enviar ao YouTube. A narração tem uma única voz, gerada no ElevenLabs a partir do texto abaixo. As imagens são slides montados com os resultados reais, gravações do painel e do firmware rodando no simulador Wokwi.

O projeto **não concorre ao pódio**, por isso o vídeo não tem a frase "QUERO CONCORRER".

**Publicação:** suba o vídeo no YouTube como **"Não listado"**, cole o link em `docs/equipe.json` (`link_video`) e no `README.md`, e rode `python docs/gerar_relatorio.py`.

| Início | Tela | Narração |
|---|---|---|
| 0:00 | Capa com integrantes → README.md | Olá, nós somos Bruna, Fábio, Fabrizzio, Gabriel e Natasha, e este é o Brisa: calor seguro na escola. |
| 0:08 | Slide: dados do problema (UNICEF, PLOS ONE, INPE) | O calor extremo já está tirando crianças da sala de aula. Em dois mil e vinte e quatro, segundo o UNICEF, as ondas de calor foram o evento climático que mais afetou a escolarização no mundo: cerca de cento e setenta e um milhões de estudantes. E, no Brasil, um estudo publicado na revista PLOS ONE estimou mais de quarenta e oito mil mortes ligadas a ondas de calor, entre dois mil e dois mil e dezoito. |
| 0:35 | Slide: a lacuna das soluções atuais | Os alertas que existem hoje falam da cidade, não da sala de aula. A coordenadora não sabe qual sala vai ficar perigosa, nem a que horas, nem o que fazer. E, na prática, só reage quando alguém passa mal. |
| 0:48 | Slide: arquitetura | O Brisa resolve isso em três camadas. Às nove da manhã, um modelo de inteligência artificial prevê o pico de calor da tarde. Durante o dia, sensores com E S P trinta e dois medem cada sala e avisam no próprio ambiente. E um backend em Python, com banco de dados S Q Lite, valida as leituras, gera alertas e mostra tudo num painel. |
| 1:11 | Slide: gráficos com dados reais | Começamos pelos dados reais: seis anos de medições, hora a hora, de dois mil e vinte a dois mil e vinte e cinco, em cinco capitais. São duzentos e sessenta e três mil registros. Em Teresina, sessenta e um por cento das horas de aula ficam em cautela extrema ou pior. Em Manaus, metade. E o pico diário subiu mais de um grau entre os dois triênios, com teste estatístico significativo. |
| 1:38 | Gravação do painel: boletim das 09h (Rio, 18/02/2025) | Este é o boletim das nove horas. No dia dezoito de fevereiro de dois mil e vinte e cinco, no Rio de Janeiro, o Brisa previu um pico de trinta e nove graus e meio: faixa de perigo. O pico real foi de trinta e nove vírgula oito. E o painel já diz o que fazer: suspender a educação física, remanejar as turmas e avisar as famílias. |
| 2:00 | Slide: métricas dos modelos + matriz de confusão | Para chegar nisso, treinamos o modelo com os dados de dois mil e vinte a dois mil e vinte e três, e testamos com dois mil e vinte e quatro e dois mil e vinte e cinco, anos que ele nunca viu. O Random Forest erra o pico, em média, em um vírgula três grau, e acerta a faixa de risco em oitenta e quatro por cento dos dias, superando a linha de base. Como o perigo é raro, calibramos um aviso preventivo que identifica oitenta e sete por cento desses dias. |
| 2:27 | Gravação do firmware real rodando no Wokwi (LEDs verde → amarelo → vermelho) | Agora, o sensor na sala. Este é o firmware real rodando no simulador Uóqui: um E S P trinta e dois com sensor D H T vinte e dois. Ele calcula o índice de calor no próprio chip, então funciona mesmo sem internet. Conforme a temperatura sobe, o LED muda de verde para amarelo, e depois para vermelho, com alerta sonoro. E cada leitura é enviada em formato djêison para o backend. |
| 2:54 | Gravação do painel: salas + terminal da demonstração | No backend, cada leitura é validada antes de entrar no banco. Leituras corrompidas são rejeitadas, e o motivo fica registrado. Nesta demonstração, com uma escola fictícia e leituras simuladas a partir do clima real, a sala do segundo andar passa mais tempo em perigo, e o Brisa indica a sala térrea para receber as turmas. |
| 3:16 | Terminal: pytest com 32 testes passando | São trinta e dois testes automatizados, todos passando. Um deles compila o código em C mais mais do E S P trinta e dois e confere se ele calcula exatamente o mesmo que o Python. E os testes ainda encontraram dois bugs reais no armazenamento das leituras, que nós corrigimos. |
| 3:35 | Slide: disciplinas e ODS | O projeto integra programação em Python, estatística, análise de dados com Pandas e Seaborn, aprendizado de máquina, banco de dados e internet das coisas. E contribui com os Objetivos de Desenvolvimento Sustentável três, quatro, onze e treze. |
| 3:53 | Slide: impacto, limitações e encerramento | Para medir o impacto, propomos acompanhar, num piloto real, as horas de aula em risco em cada sala e a antecedência dos avisos. Sabemos das limitações: os dados externos têm baixa resolução, e as leituras internas da demonstração são simuladas. O próximo passo é instalar sensores de verdade. Brisa: menos calor, mais aula. Obrigado! |

## Checklist
- [x] Integrantes e README nos primeiros segundos
- [x] Integração entre disciplinas (cena 11)
- [x] Demonstração prática: painel, firmware no Wokwi, terminal e testes
- [x] Duração ≤ 5 min (4:17)
- [x] Dados simulados chamados de simulados na narração
- [ ] Publicar no YouTube como "Não listado" e colocar o link no PDF e no README
