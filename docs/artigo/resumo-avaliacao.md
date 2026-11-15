# Resumo da avaliação

Comparação entre o RAG vetorial e o GraphRAG nas 15 perguntas de avaliação, com as respostas salvas em `data/avaliacao/resultados/respostas.json` e a classificação de `data/avaliacao/classificacao.json`. O relatório completo, com o resultado de cada pergunta, está em `docs/avaliacao-resultados.md`.

| Modo | Tipo | Perguntas | Evidência recuperada | Caminho completo | Recusa correta | Correta | Incompleta | Alucinada |
|---|---|---|---|---|---|---|---|---|
| Vetorial | Um salto | 5 | 0% | 0% | n/a | 0 | 5 | 0 |
| Vetorial | Multi-hop | 7 | 0% | 0% | n/a | 1 | 6 | 0 |
| Vetorial | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |
| GraphRAG | Um salto | 5 | 0% | 0% | n/a | 0 | 5 | 0 |
| GraphRAG | Multi-hop | 7 | 14% | 29% | n/a | 2 | 5 | 0 |
| GraphRAG | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |

Evidência recuperada quer dizer que todos os trechos do gabarito estão nas fontes da resposta. Caminho completo quer dizer que todas as relações do gabarito estão no subgrafo. O modo vetorial não monta subgrafo, então o caminho completo dele é sempre 0%.

## Leitura dos resultados

Nas perguntas multi-hop, o GraphRAG deu 2 respostas corretas em 7, e o vetorial, 1. A diferença está na P08. O vetorial recusou, porque a busca não trouxe o trecho do prêmio, e o GraphRAG chegou a esse trecho seguindo as relações do grafo, do C ao B, do B a Ken Thompson e dele ao Prêmio Turing. O GraphRAG também montou o caminho completo do gabarito em 2 das 7 perguntas multi-hop. Nas perguntas de um salto, nenhum dos modos acertou, porque os artigos dessas perguntas não estavam no banco. Os dois modos recusaram as 3 perguntas sem resposta, e nenhuma resposta foi classificada como alucinada. Quando o contexto não tinha a resposta, o sistema recusou em vez de inventar.

## Limite da amostra

A amostra tem 15 perguntas: 5 de um salto, 7 multi-hop e 3 sem resposta. O banco tinha 4 documentos quando as respostas foram geradas, os artigos do C, do C++, de Dennis Ritchie e de Ken Thompson. Por isso, 21 das 24 respostas a perguntas com resposta são recusas, e 20 delas são de perguntas que dependem de algum artigo que não estava carregado. Os números indicam tendência, e não diferença estatisticamente significativa.

## Erros analisados

Na P08, no modo vetorial, a busca não trouxe o trecho do prêmio, que não cita o C nem o B, e o sistema recusou, enquanto o GraphRAG chegou ao mesmo trecho pelo grafo.

Na P07, no modo GraphRAG, a expansão chegou ao Simula, a linguagem que influenciou o C++, mas parou aí, porque nenhuma fonte liga o Simula a quem o criou.

Na P12, no modo GraphRAG, a Cypher filtrou o Python pelo nome, sem um id, e não trouxe nenhum caminho com ele, então o primeiro salto da pergunta nunca chegou ao contexto.
