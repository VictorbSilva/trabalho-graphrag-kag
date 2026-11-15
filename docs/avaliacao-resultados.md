# Avaliação: RAG vetorial vs GraphRAG

Gerado por `python -m src.avaliacao.comparar` em 2026-11-15 19:07, com as 15 perguntas de [data/avaliacao/perguntas.json](../data/avaliacao/perguntas.json) nos modos `vetorial` e `graphrag`. As respostas completas ficam em [data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). Os números dependem do que estava carregado no Neo4j quando o executor rodou.

A classificação manual fica em [data/avaliacao/classificacao.json](../data/avaliacao/classificacao.json) e sobrevive a novas execuções do executor. A planilha para preenchê-la está em [docs/avaliacao-planilha.md](avaliacao-planilha.md).

## Como ler

- **Evidência recuperada**: todos os trechos de `evidencias` da pergunta aparecem dentro de alguma fonte da resposta (espaços normalizados). Quando falta algum, entre parênteses vai quantos foram achados.
- **Caminho completo**: todas as triplas de `caminho_esperado` aparecem, na direção do schema, nas arestas do subgrafo da resposta. O modo `vetorial` não monta subgrafo.
- **Recusa correta**: só nas perguntas `sem_resposta`, a resposta diz "Não encontrei essa informação no dataset."
- **n/a**: a métrica não se aplica ao tipo da pergunta. **n/d**: sem dados para calcular.
- **Classificação (manual)**: correta, incompleta ou alucinada, lida de `data/avaliacao/classificacao.json` e preenchida por quem conferir a resposta contra o gabarito. Nas perguntas `sem_resposta`, cujo gabarito é recusar, a recusa correta vira correta e qualquer outra resposta vira alucinada.

## Resultado por pergunta

| ID | Tipo | Modo | Evidência recuperada | Caminho completo | Recusa correta | Confiança | Classificação (manual) |
|---|---|---|---|---|---|---|---|
| P01 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P01 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P02 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P02 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P03 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P03 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P04 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P04 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P05 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P05 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P06 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P06 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P07 | multi_hop | vetorial | não (1/3) | não (0/5) | n/a | baixa (0.00) | incompleta |
| P07 | multi_hop | graphrag | não (1/3) | não (1/5) | n/a | baixa (0.00) | incompleta |
| P08 | multi_hop | vetorial | não (1/3) | não (0/3) | n/a | baixa (0.00) | incompleta |
| P08 | multi_hop | graphrag | não (2/3) | sim | n/a | media (0.63) | correta |
| P09 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P09 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P10 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P10 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P11 | multi_hop | vetorial | não (2/3) | não (0/4) | n/a | baixa (0.35) | correta |
| P11 | multi_hop | graphrag | sim | sim | n/a | media (0.65) | correta |
| P12 | multi_hop | vetorial | não (1/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P12 | multi_hop | graphrag | não (1/2) | não (1/2) | n/a | baixa (0.00) | incompleta |
| P13 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P13 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |
| P14 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P14 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |
| P15 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P15 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |

## Resumo

| Modo | Tipo | Perguntas | Com erro | Evidência recuperada | Caminho completo |
|---|---|---|---|---|---|
| vetorial | um_salto | 5 | 0 | 0% | 0% |
| vetorial | multi_hop | 7 | 0 | 0% | 0% |
| graphrag | um_salto | 5 | 0 | 0% | 0% |
| graphrag | multi_hop | 7 | 0 | 14% | 29% |

| Modo | Perguntas sem resposta | Com erro | Recusa correta |
|---|---|---|---|
| vetorial | 3 | 0 | 100% |
| graphrag | 3 | 0 | 100% |

| Modo | Tipo | Perguntas | Classificadas | Correta | Incompleta | Alucinada |
|---|---|---|---|---|---|---|
| vetorial | um_salto | 5 | 5 | 0 | 5 | 0 |
| vetorial | multi_hop | 7 | 7 | 1 | 6 | 0 |
| vetorial | sem_resposta | 3 | 3 | 3 | 0 | 0 |
| graphrag | um_salto | 5 | 5 | 0 | 5 | 0 |
| graphrag | multi_hop | 7 | 7 | 2 | 5 | 0 |
| graphrag | sem_resposta | 3 | 3 | 3 | 0 | 0 |

Limite da amostra: 15 perguntas; os números indicam tendência, não diferença estatisticamente significativa.

## Análise de erros

Três casos escolhidos a partir da tabela acima.

Esta execução rodou com a semente no banco: 4 documentos (C, C++, Dennis Ritchie e Ken Thompson). Das 24 respostas a perguntas com resposta, 21 são recusas. Dessas, 18 vêm de perguntas cujo documento principal não está no banco (P01 a P06, P09, P10 e P12, nos dois modos). Os casos abaixo são os que a semente permitia responder ao menos em parte.

### Caso 1

- Pergunta e modo: P08, "Que prêmio recebeu quem criou a linguagem que deu origem ao C?", no modo vetorial, comparado ao graphrag.
- O que aconteceu: o vetorial recusou. Os cinco trechos da busca vieram dos artigos do C e do C++. Um deles diz que o C veio do B, mas nenhum diz quem criou o B nem que prêmio essa pessoa recebeu. O graphrag respondeu certo, com confiança média (0,63). A expansão foi do C ao B, do B a Ken Thompson e dele ao Prêmio Turing, e trouxe como fontes os trechos dos artigos de Ken Thompson e Dennis Ritchie que sustentam essas relações (F6 a F8, sem score).
- Causa provável: a busca vetorial só traz trechos parecidos com a pergunta. O trecho que fala do prêmio não cita o C nem o B, então não fica entre os cinco primeiros. É o caso que a expansão multi-hop resolve: o trecho entra porque sustenta uma relação do caminho, e não por se parecer com a pergunta.

### Caso 2

- Pergunta e modo: P07, "Além do C, o C++ foi influenciado por outra linguagem de programação. Que prêmio receberam os criadores dessa linguagem?", no modo graphrag.
- O que aconteceu: recusou nos dois modos. No graphrag, o contexto tinha o caminho C2, em que o C++ é influenciado pelo Simula. A Cypher gerada pedia a linguagem que influenciou o C++, sem ser o C, seguida de quem a criou e do prêmio, e não devolveu nenhum caminho. A confiança ficou em 0, embora a similaridade do melhor caminho com a pergunta fosse 0,76.
- Causa provável: a semente não tem os criadores do Simula nem o prêmio deles. No grafo, o Simula só aparece como influência do C++. O sistema achou a linguagem intermediária, mas não tinha como dar os dois saltos seguintes. O LLM seguiu a instrução de recusar quando o contexto não tem a resposta e não deu a parte que tinha, que a linguagem é o Simula.

### Caso 3

- Pergunta e modo: P12, "A linguagem Python tem parte da sintaxe derivada de outra linguagem. Em qual organização essa outra linguagem foi criada?", no modo graphrag.
- O que aconteceu: recusou. Não há entidade Python no banco, e a Cypher, que procurou o Python pelo nome, não devolveu nada. Mesmo assim a expansão devolveu cinco caminhos, todos entre C++, C, B, Simula, Bell Labs, Ken Thompson e Dennis Ritchie, com similaridade máxima de 0,33 com a pergunta. A métrica de caminho completo marcou 1/2, porque a aresta do C ao Bell Labs está na semente, embora a resposta não a use.
- Causa provável: o artigo do Python não está na semente. A expansão sempre parte dos trechos da busca, e a busca sempre devolve cinco trechos, mesmo sem relação com a pergunta (o melhor teve score 0,72, cosseno 0,45). Os caminhos que vêm daí ocupam o contexto sem ajudar, e a recusa dependeu só do LLM.

