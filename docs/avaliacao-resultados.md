# Avaliação: RAG vetorial vs GraphRAG

Gerado por `python -m src.avaliacao.comparar` em 2026-11-15 17:32, com as 15 perguntas de [data/avaliacao/perguntas.json](../data/avaliacao/perguntas.json) nos modos `vetorial` e `graphrag`. As respostas completas ficam em [data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). Os números dependem do que estava carregado no Neo4j quando o executor rodou.

Rodar o executor de novo sobrescreve este arquivo, inclusive a classificação manual.

## Como ler

- **Evidência recuperada**: todos os trechos de `evidencias` da pergunta aparecem dentro de alguma fonte da resposta (espaços normalizados). Quando falta algum, entre parênteses vai quantos foram achados.
- **Caminho completo**: todas as triplas de `caminho_esperado` aparecem, na direção do schema, nas arestas do subgrafo da resposta. O modo `vetorial` não monta subgrafo.
- **Recusa correta**: só nas perguntas `sem_resposta`, a resposta diz "Não encontrei essa informação no dataset."
- **n/a**: a métrica não se aplica ao tipo da pergunta. **n/d**: sem dados para calcular.
- **Classificação (manual)**: correta, incompleta ou alucinada, preenchida por quem conferir a resposta contra o gabarito.

## Resultado por pergunta

| ID | Tipo | Modo | Evidência recuperada | Caminho completo | Recusa correta | Confiança | Classificação (manual) |
|---|---|---|---|---|---|---|---|
| P01 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P01 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P02 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P02 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P03 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P03 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P04 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P04 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P05 | um_salto | vetorial | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P05 | um_salto | graphrag | não (0/1) | não (0/1) | n/a | baixa (0.00) |  |
| P06 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P06 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P07 | multi_hop | vetorial | não (1/3) | não (0/5) | n/a | media (0.52) |  |
| P07 | multi_hop | graphrag | não (1/3) | não (1/5) | n/a | alta (0.75) |  |
| P08 | multi_hop | vetorial | não (1/3) | não (0/3) | n/a | baixa (0.00) |  |
| P08 | multi_hop | graphrag | não (2/3) | sim | n/a | media (0.63) |  |
| P09 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P09 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P10 | multi_hop | vetorial | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P10 | multi_hop | graphrag | não (0/2) | não (0/2) | n/a | baixa (0.00) |  |
| P11 | multi_hop | vetorial | não (2/3) | não (0/4) | n/a | baixa (0.35) |  |
| P11 | multi_hop | graphrag | sim | sim | n/a | media (0.65) |  |
| P12 | multi_hop | vetorial | não (1/2) | não (0/2) | n/a | baixa (0.00) |  |
| P12 | multi_hop | graphrag | não (1/2) | não (1/2) | n/a | baixa (0.00) |  |
| P13 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) |  |
| P13 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) |  |
| P14 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) |  |
| P14 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) |  |
| P15 | sem_resposta | vetorial | n/a | n/a | sim | baixa (0.00) |  |
| P15 | sem_resposta | graphrag | n/a | n/a | sim | baixa (0.00) |  |

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

