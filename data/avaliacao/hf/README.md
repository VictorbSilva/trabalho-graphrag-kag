---
license: cc-by-sa-4.0
language:
- pt
task_categories:
- question-answering
tags:
- rag
- graphrag
- knowledge-graph
- hallucination-evaluation
size_categories:
- n<1K
pretty_name: Avaliação GraphRAG e KAG, história da computação
configs:
- config_name: perguntas
  data_files:
  - split: test
    path: perguntas.jsonl
- config_name: respostas
  data_files:
  - split: test
    path: respostas.jsonl
---

# Avaliação GraphRAG e KAG: história da computação

Conjunto de avaliação de um sistema de perguntas e respostas sobre a história da computação, construído a partir de artigos da Wikipédia em português. Serve para comparar o RAG vetorial com o GraphRAG em perguntas de um salto, perguntas multi-hop (2 ou 3 relações) e perguntas sem resposta no corpus, e para estudar quando cada modo recusa, acerta ou alucina.

O conjunto tem duas partes:

- `perguntas`: 15 perguntas com gabarito, incluindo o caminho esperado no grafo e os trechos literais que sustentam cada fato;
- `respostas`: as 60 respostas do sistema (15 perguntas x 2 modos x 2 bancos), cada uma com a classificação manual e o contexto que o LLM recebeu.

## Como carregar

```python
from datasets import load_dataset

perguntas = load_dataset("VictorbSilva/graphrag-kag-historia-computacao-avaliacao", "perguntas", split="test")
respostas = load_dataset("VictorbSilva/graphrag-kag-historia-computacao-avaliacao", "respostas", split="test")
```

## Campos

### perguntas

| Campo | Descrição |
|---|---|
| `id` | P01 a P15 |
| `pergunta` | texto enviado ao sistema |
| `tipo` | `um_salto` (P01 a P05), `multi_hop` (P06 a P12) ou `sem_resposta` (P13 a P15) |
| `saltos` | número de relações na menor cadeia entre a pergunta e a resposta (0 nas sem resposta) |
| `resposta_esperada` | gabarito em texto livre |
| `caminho_esperado` | triplas `{origem, tipo, destino}` com ids canônicos, na direção do schema (vazio nas sem resposta) |
| `evidencias` | trechos literais dos artigos (`artigo`, `trecho`) que sustentam cada fato |

### respostas

| Campo | Descrição |
|---|---|
| `id_pergunta` | id da pergunta em `perguntas` |
| `banco` | `semente` (4 artigos anotados à mão) ou `completo` (31 artigos) |
| `modo` | `vetorial` ou `graphrag` |
| `modelo_llm` | modelo que gerou a resposta |
| `resposta` | texto gerado, com as citações `[F1]` (trecho) e `[C1]` (caminho) |
| `classificacao` | `correta`, `incompleta` ou `alucinada` (manual) |
| `trechos` | trechos entregues ao LLM: `id` (F1, F2...), `chunk_id`, `documento`, `url`, `trecho` e `score`. O `score` é nulo nos trechos que vieram pelo grafo, e não pela busca vetorial |
| `caminhos` | caminhos do grafo entregues ao LLM: `id` (C1, C2...), `nos`, `relacoes` e `fontes` (chunk_ids que sustentam o caminho). Vazio no modo vetorial |

Os trechos e caminhos são todo o contexto que o LLM recebeu, e não só os citados na resposta. Assim dá para ver o que o sistema tinha em mãos quando recusou.

## Como foi construído

**Fonte.** Uma lista de 32 artigos da Wikipédia em português que se citam entre si: pioneiros e o Prêmio Turing, a família C e Unix, Java e Sun, Python, Lisp e linguagens históricas, Linux e a web. Os artigos foram divididos em trechos de até 450 caracteres. As entidades (`Pessoa`, `Organizacao`, `Tecnologia`, `Premio`) e as relações (`CRIOU`, `TRABALHOU_EM`, `DESENVOLVIDA_EM`, `INFLUENCIADA_POR`, `RECEBEU`) foram extraídas com LLM (Groq com `openai/gpt-oss-120b` e Gemini com `gemini-3.5-flash-lite`) e carregadas no Neo4j.

**Perguntas.** Escritas a partir dos textos dos artigos, sem olhar respostas do sistema, para reduzir o viés de quem construiu a recuperação. As perguntas sem resposta usam termos que não aparecem em nenhum artigo (Rust, Margaret Hamilton, Kotlin), e a resposta certa é dizer que não encontrou a informação.

**Rodadas.**

| Banco | Artigos carregados | Embeddings | LLM das respostas |
|---|---|---|---|
| `semente` | 4 (C, C++, Dennis Ritchie e Ken Thompson), anotados à mão | `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) | `claude-opus-5-5-fast`, pela Abacus RouteLLM, temperatura 0 |
| `completo` | 31 dos 32 previstos (o do MIT ficou incompleto) | `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) | `claude-haiku-5-5`, pela Abacus RouteLLM, temperatura 0 |

**Classificação.** Manual, sem LLM juiz. Cada resposta foi comparada com o gabarito e classificada como correta, incompleta ou alucinada. Uma recusa numa pergunta que tem resposta conta como incompleta. Nas perguntas sem resposta, cujo gabarito é recusar, a recusa vira correta e qualquer outra resposta vira alucinada.

**Métricas automáticas** (nas tabelas abaixo):

- evidência recuperada: todos os trechos de `evidencias` aparecem dentro de algum trecho entregue ao LLM;
- caminho completo: todas as triplas de `caminho_esperado` aparecem, na direção do schema, no subgrafo da resposta. O modo vetorial não monta subgrafo;
- recusa correta: nas perguntas sem resposta, a resposta diz "Não encontrei essa informação no dataset."

## Resultados

Banco `semente`:

| Modo | Tipo | Perguntas | Evidência recuperada | Caminho completo | Recusa correta | Correta | Incompleta | Alucinada |
|---|---|---|---|---|---|---|---|---|
| Vetorial | Um salto | 5 | 0% | 0% | n/a | 0 | 5 | 0 |
| Vetorial | Multi-hop | 7 | 0% | 0% | n/a | 1 | 6 | 0 |
| Vetorial | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |
| GraphRAG | Um salto | 5 | 0% | 0% | n/a | 0 | 5 | 0 |
| GraphRAG | Multi-hop | 7 | 14% | 29% | n/a | 2 | 5 | 0 |
| GraphRAG | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |

Banco `completo`:

| Modo | Tipo | Perguntas | Evidência recuperada | Caminho completo | Recusa correta | Correta | Incompleta | Alucinada |
|---|---|---|---|---|---|---|---|---|
| Vetorial | Um salto | 5 | 40% | 0% | n/a | 3 | 2 | 0 |
| Vetorial | Multi-hop | 7 | 0% | 0% | n/a | 0 | 7 | 0 |
| Vetorial | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |
| GraphRAG | Um salto | 5 | 80% | 80% | n/a | 5 | 0 | 0 |
| GraphRAG | Multi-hop | 7 | 0% | 14% | n/a | 2 | 4 | 1 |
| GraphRAG | Sem resposta | 3 | n/a | n/a | 100% | 3 | 0 | 0 |

Na semente, o GraphRAG acertou uma pergunta multi-hop a mais que o vetorial: na P08, seguiu o grafo do C ao B, do B a Ken Thompson e dele ao Prêmio Turing, enquanto a busca vetorial não trouxe o trecho do prêmio. Com o banco completo, o GraphRAG acertou as cinco perguntas de um salto e duas das sete multi-hop, contra três e nenhuma do vetorial. Nos dois bancos, os dois modos recusaram as três perguntas sem resposta.

## Limitações

- **Só 15 perguntas.** Os números indicam tendência, e não diferença estatisticamente significativa.
- **Na semente, o banco tinha só 4 artigos.** 21 das 24 respostas a perguntas com resposta são recusas, e 20 delas são de perguntas que dependem de algum artigo que não estava carregado.
- **O banco e o modelo mudaram juntos entre as rodadas.** As diferenças entre semente e completo não podem ser atribuídas só ao banco.
- **A extração tem relações erradas.** Das 964 ocorrências de relações extraídas, 907 ainda estão pendentes de revisão.
- **A única alucinação veio de uma relação extraída errada.** Na P12 do banco completo, modo GraphRAG, o sistema respondeu que o C foi desenvolvido na Nokia. A resposta seguiu uma relação `DESENVOLVIDA_EM` tirada de um trecho que diz que o prédio de Murray Hill, hoje da Nokia, foi o local de desenvolvimento do C.
## Créditos e licença

Os textos são da [Wikipédia em português](https://pt.wikipedia.org), sob a licença [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt-br). Os autores de cada artigo estão no histórico da respectiva página, e o título, a URL e a revisão exata de cada artigo estão em `data/bruto/manifesto.json` do repositório. Este conjunto, derivado deles, segue a mesma licença.

Trabalho em grupo de Gabriel Xavier, Victor Gabriel, Nicolas Brito, Pedro Jorge e Patrick Duarte.

- Repositório: [github.com/VictorbSilva/trabalho-graphrag-kag](https://github.com/VictorbSilva/trabalho-graphrag-kag)
- Artigo: [docs/artigo/artigo.pdf](https://github.com/VictorbSilva/trabalho-graphrag-kag/blob/main/docs/artigo/artigo.pdf)
- Script que gerou estes arquivos: `src/avaliacao/exportar_hf.py`
