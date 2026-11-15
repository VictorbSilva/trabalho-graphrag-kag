# Avaliação: RAG vetorial vs GraphRAG

Gerado por `python -m src.avaliacao.comparar` em 2026-11-15 19:21, com as 15 perguntas de [data/avaliacao/perguntas.json](../data/avaliacao/perguntas.json) nos modos `vetorial` e `graphrag`. As respostas completas ficam em [data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). Os números dependem do que estava carregado no Neo4j quando o executor rodou.

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

Três casos escolhidos a partir da tabela acima, cada um com a falha numa etapa diferente: busca, expansão e Cypher. Os três foram classificados como incompletos, porque o sistema recusou. Nenhuma resposta foi classificada como alucinada.

### Caso 1

- Pergunta e modo: P08, "Que prêmio recebeu quem criou a linguagem que deu origem ao C?", no modo vetorial. Classe: incompleta.
- O que aconteceu: o sistema recusou. A busca trouxe cinco trechos, todos dos artigos do C e do C++, com score máximo de 0,83. Das três evidências do gabarito, só veio a que diz que o C foi obtido a partir do B (F1). Faltaram a que diz que Thompson criou o B e a do Prêmio Turing. O modo vetorial não monta caminho, então nenhuma das três triplas aparece.
- Causa provável: falha na busca. O trecho do prêmio, do artigo de Dennis Ritchie, não cita o C nem o B e não ficou entre os cinco mais parecidos com a pergunta. Ele está no banco: na mesma pergunta, o modo graphrag o trouxe como F6, sem score, porque ele sustenta a relação RECEBEU de um caminho, e respondeu certo.

### Caso 2

- Pergunta e modo: P07, "Além do C, o C++ foi influenciado por outra linguagem de programação. Que prêmio receberam os criadores dessa linguagem?", no modo graphrag. Classe: incompleta.
- O que aconteceu: o sistema recusou. A busca trouxe o trecho do C++ que cita o Simula 67 (F3), uma das três evidências. A expansão chegou ao Simula: o caminho C2 tem a relação em que o C++ é influenciado pelo Simula, uma das cinco triplas do gabarito. Nenhum caminho sai do Simula para quem o criou, e Kristen Nygaard e Ole-Johan Dahl não estão entre os nós consultados. A Cypher gerada pedia esse percurso, da linguagem que influenciou o C++, sem ser o C, a quem a criou e ao prêmio, mas nenhum caminho da resposta tem esse formato.
- Causa provável: falha na expansão, que parou no primeiro dos três saltos. As fontes vêm só dos artigos do C, do C++, de Dennis Ritchie e de Ken Thompson, e nenhuma delas liga o Simula a quem o criou. A geração recusou por inteiro, como manda a instrução, e não aproveitou a parte que o contexto tinha, que a linguagem é o Simula.

### Caso 3

- Pergunta e modo: P12, "A linguagem Python tem parte da sintaxe derivada de outra linguagem. Em qual organização essa outra linguagem foi criada?", no modo graphrag. Classe: incompleta.
- O que aconteceu: o sistema recusou. A busca trouxe a evidência de que o C foi criado no Bell Labs (F2), mas não a que liga a sintaxe do Python ao C. A expansão trouxe a aresta do C ao Bell Labs, uma das duas triplas do gabarito, dentro de cinco caminhos entre C++, C, B, Simula, Bell Labs, Ken Thompson e Dennis Ritchie, com similaridade máxima de 0,33 com a pergunta. A Cypher gerada filtra o Python pelo nome, com `toLower(t.name) = 'python'`, e o Python não aparece entre os nós consultados.
- Causa provável: falha na Cypher, que é o passo que deveria ancorar a consulta no Python. A consulta usa o nome, e não um id, o que indica que nenhuma entidade Python foi encontrada antes da geração, e ela não trouxe nenhum caminho com o Python. A expansão, que parte dos trechos da busca, só alcançou o segundo salto. A recusa é coerente com o contexto que o LLM recebeu, mas o primeiro salto nunca chegou a ele.

