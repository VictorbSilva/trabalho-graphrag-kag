# Avaliação: RAG vetorial vs GraphRAG

Gerado por `python -m src.avaliacao.comparar` em 2026-11-16 05:51, com as 15 perguntas de [data/avaliacao/perguntas.json](../data/avaliacao/perguntas.json) nos modos `vetorial` e `graphrag`. As respostas completas ficam em [data/avaliacao/resultados/completo/respostas.json](../data/avaliacao/resultados/completo/respostas.json). Os números dependem do que estava carregado no Neo4j quando o executor rodou.

A classificação manual fica em [data/avaliacao/resultados/completo/classificacao.json](../data/avaliacao/resultados/completo/classificacao.json) e sobrevive a novas execuções do executor. A planilha para preenchê-la está em [docs/avaliacao-planilha-completo.md](avaliacao-planilha-completo.md).

## Como ler

- **Evidência recuperada**: todos os trechos de `evidencias` da pergunta aparecem dentro de alguma fonte da resposta (espaços normalizados). Quando falta algum, entre parênteses vai quantos foram achados.
- **Caminho completo**: todas as triplas de `caminho_esperado` aparecem, na direção do schema, nas arestas do subgrafo da resposta. O modo `vetorial` não monta subgrafo.
- **Recusa correta**: só nas perguntas `sem_resposta`, a resposta diz "Não encontrei essa informação no dataset."
- **n/a**: a métrica não se aplica ao tipo da pergunta. **n/d**: sem dados para calcular.
- **Classificação (manual)**: correta, incompleta ou alucinada, lida de `data/avaliacao/resultados/completo/classificacao.json` e preenchida por quem conferir a resposta contra o gabarito. Nas perguntas `sem_resposta`, cujo gabarito é recusar, a recusa correta vira correta e qualquer outra resposta vira alucinada.

## Resultado por pergunta

| ID | Tipo | Modo | Evidência recuperada | Caminho completo | Recusa correta | Confiança | Classificação (manual) |
|---|---|---|---|---|---|---|---|
| P01 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | media (0.52) | correta |
| P01 | um_salto | graphrag | sim | não (0/1) | n/a | alta (0.75) | correta |
| P02 | um_salto | vetorial | sim | não (0/1) | n/a | media (0.50) | correta |
| P02 | um_salto | graphrag | sim | sim | n/a | media (0.69) | correta |
| P03 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P03 | um_salto | graphrag | não (0/1) | sim | n/a | alta (0.71) | correta |
| P04 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) | incompleta |
| P04 | um_salto | graphrag | sim | sim | n/a | media (0.54) | correta |
| P05 | um_salto | vetorial | sim | não (0/1) | n/a | media (0.40) | correta |
| P05 | um_salto | graphrag | sim | sim | n/a | media (0.66) | correta |
| P06 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P06 | multi_hop | graphrag | não (1/2) | não (1/2) | n/a | media (0.62) | correta |
| P07 | multi_hop | vetorial | não (0/3) | não (0/5) | n/a | baixa (0.00) | incompleta |
| P07 | multi_hop | graphrag | não (0/3) | não (0/5) | n/a | baixa (0.00) | incompleta |
| P08 | multi_hop | vetorial | não (1/3) | não (0/3) | n/a | baixa (0.00) | incompleta |
| P08 | multi_hop | graphrag | não (1/3) | sim | n/a | baixa (0.00) | incompleta |
| P09 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P09 | multi_hop | graphrag | não (1/2) | não (1/2) | n/a | baixa (0.00) | incompleta |
| P10 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | media (0.51) | incompleta |
| P10 | multi_hop | graphrag | não (1/2) | não (0/2) | n/a | media (0.67) | correta |
| P11 | multi_hop | vetorial | não (0/3) | não (0/4) | n/a | media (0.54) | incompleta |
| P11 | multi_hop | graphrag | não (0/3) | não (2/4) | n/a | alta (0.80) | incompleta |
| P12 | multi_hop | vetorial | não (1/2) | não (0/2) | n/a | baixa (0.00) | incompleta |
| P12 | multi_hop | graphrag | não (1/2) | não (1/2) | n/a | alta (0.71) | alucinada |
| P13 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P13 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |
| P14 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P14 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |
| P15 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) | correta |
| P15 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) | correta |

## Resumo

| Modo | Tipo | Perguntas | Com erro | Evidência recuperada | Caminho completo |
|---|---|---|---|---|---|
| vetorial | um_salto | 5 | 0 | 40% | 0% |
| vetorial | multi_hop | 7 | 0 | 0% | 0% |
| graphrag | um_salto | 5 | 0 | 80% | 80% |
| graphrag | multi_hop | 7 | 0 | 0% | 14% |

| Modo | Perguntas sem resposta | Com erro | Recusa correta |
|---|---|---|---|
| vetorial | 3 | 0 | 100% |
| graphrag | 3 | 0 | 100% |

| Modo | Tipo | Perguntas | Classificadas | Correta | Incompleta | Alucinada |
|---|---|---|---|---|---|---|
| vetorial | um_salto | 5 | 5 | 3 | 2 | 0 |
| vetorial | multi_hop | 7 | 7 | 0 | 7 | 0 |
| vetorial | sem_resposta | 3 | 3 | 3 | 0 | 0 |
| graphrag | um_salto | 5 | 5 | 5 | 0 | 0 |
| graphrag | multi_hop | 7 | 7 | 2 | 4 | 1 |
| graphrag | sem_resposta | 3 | 3 | 3 | 0 | 0 |

Limite da amostra: 15 perguntas; os números indicam tendência, não diferença estatisticamente significativa.

## Análise de erros

Três casos escolhidos a partir da tabela acima.

### Caso 1

- Pergunta e modo:
- O que aconteceu:
- Causa provável:

### Caso 2

- Pergunta e modo:
- O que aconteceu:
- Causa provável:

### Caso 3

- Pergunta e modo:
- O que aconteceu:
- Causa provável:

