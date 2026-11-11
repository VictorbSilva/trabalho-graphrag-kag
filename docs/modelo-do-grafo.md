# Modelo do grafo (LPG no Neo4j)

Responsável: Nicolas. Requisitos: R03 a R09 e R20.

**Domínio:** história da computação, a partir de cerca de 30 artigos da Wikipédia em português (licença CC BY-SA). Os rótulos e relações do domínio estão na seção [Rótulos e relações do domínio](#rótulos-e-relações-do-domínio). A versão legível por código, usada pelo prompt de extração e pelo prompt do Text-to-Cypher, é [`neo4j/dominio.json`](../neo4j/dominio.json). Constraints e índices estão em `neo4j/schema/`.

## Visão geral

O grafo tem duas camadas ligadas entre si:

- **Grafo léxico:** os documentos originais quebrados em trechos (`Chunk`), cada um com seu embedding. É daqui que sai a busca vetorial e a procedência.
- **Grafo de domínio:** as entidades e relações extraídas pelo LLM. É aqui que acontece a travessia multi-hop e onde rodam os algoritmos do GDS.

A ligação entre as camadas (`MENTIONS` e `source_chunk_ids`) funciona como um índice nos dois sentidos: dá para ir de um trecho para as entidades que ele cita e de uma relação para os trechos que a justificam. É o que permite o grounding (R21) e a exibição de procedência (R28), e é a ideia de indexação mútua do KAG.

```mermaid
graph LR
  D[":Document<br/>id, title, source"]
  C1[":Chunk<br/>id, index, text, embedding"]
  C2[":Chunk"]
  P[":Entity:Pessoa<br/>Dennis Ritchie"]
  T[":Entity:Tecnologia<br/>C"]
  O[":Entity:Organizacao<br/>Bell Labs"]
  R[":Entity:Premio<br/>Prêmio Turing"]
  T2[":Entity:Tecnologia<br/>C++"]

  C1 -- PART_OF --> D
  C2 -- PART_OF --> D
  C1 -- NEXT --> C2
  C1 -- MENTIONS --> P
  C1 -- MENTIONS --> T
  C2 -- MENTIONS --> O
  P -- "CRIOU<br/>{source_chunk_ids}" --> T
  P -- TRABALHOU_EM --> O
  T -- DESENVOLVIDA_EM --> O
  P -- RECEBEU --> R
  T2 -- INFLUENCIADA_POR --> T
```

Exemplo de caminho de 3 saltos: C++ `INFLUENCIADA_POR` C, que Dennis Ritchie `CRIOU`, e Dennis Ritchie `RECEBEU` o Prêmio Turing.

## Nós

| Rótulo | Propriedades | Observações |
|---|---|---|
| `Document` | `id` (único), `title`, `source` | Um por arquivo do dataset. `source` guarda a origem (URL ou caminho). |
| `Chunk` | `id` (único), `index`, `text`, `embedding` | Trecho do documento. `index` é a posição dentro do documento. |
| `Entity` + rótulo do domínio | `id` (único), `name`, `type`, `aliases`, `description`, `embedding`, `pagerank`, `community` | `id` é a forma canônica gerada pela resolução de entidades, ex.: `pessoa:maria_silva`. `type` repete o rótulo do domínio. `pagerank` e `community` são gravados pelo GDS. |

## Relações

| Tipo | De → Para | Propriedades | Para que serve |
|---|---|---|---|
| `PART_OF` | `Chunk` → `Document` | | Saber de qual documento veio cada trecho |
| `NEXT` | `Chunk` → `Chunk` | | Expandir o contexto para o trecho vizinho |
| `MENTIONS` | `Chunk` → `Entity` | | Ligar texto e grafo (procedência e busca híbrida) |
| relações do domínio | `Entity` → `Entity` | `source_chunk_ids` | Fatos extraídos. `source_chunk_ids` lista os trechos que justificam a relação. |

## Constraints e índices

| Nome | Tipo | Alvo | Requisito |
|---|---|---|---|
| `document_id_unique` | Unicidade | `Document.id` | R05 |
| `chunk_id_unique` | Unicidade | `Chunk.id` | R05 |
| `entity_id_unique` | Unicidade | `Entity.id` | R05, R12 |
| `entity_name`, `entity_type`, `entity_pagerank`, `entity_community`, `document_source` | Range | propriedades usadas em filtros e ordenação | R06 |
| `entity_search` | Fulltext (analyzer `brazilian`) | `Entity.name`, `aliases`, `description` | R07 |
| `chunk_text` | Fulltext (analyzer `brazilian`) | `Chunk.text` | R07 |
| `chunk_embedding` | Vector (384 dimensões, cosseno) | `Chunk.embedding` | R08 |
| `entity_embedding` | Vector (384 dimensões, cosseno) | `Entity.embedding` (vazio nesta entrega) | R08 |

Para conferir no banco (evidência para o artigo):

```cypher
SHOW CONSTRAINTS;
SHOW INDEXES;
```

## Algoritmos de grafo (R20)

Rodam sobre uma projeção só com os nós `Entity` e as relações entre eles, depois da ingestão:

```bash
docker compose run --rm neo4j-gds
```

- **PageRank** → `Entity.pagerank`: importância da entidade. Usado para ranquear o que entra no contexto do LLM.
- **Louvain** → `Entity.community`: comunidade (tema). Usado para enriquecer o contexto e colorir o subgrafo na interface.
- **Caminho mais curto:** feito em Cypher na hora da pergunta (consulta 4 de `neo4j/consultas/exemplos.cypher`).

## Decisões de modelagem (para o artigo)

1. **Rótulo genérico `Entity` + rótulo do domínio.** Uma única constraint em `Entity.id` impede duplicatas de qualquer tipo, e os índices fulltext e vetorial cobrem todas as entidades de uma vez. O rótulo do domínio (`Pessoa`, `Organizacao`...) continua disponível para as consultas Cypher geradas pelo LLM.
2. **Procedência na própria relação.** `source_chunk_ids` evita criar um nó intermediário para cada fato e mantém a travessia multi-hop curta.
3. **Range em vez de BTree.** O enunciado pede BTree/Range. No Neo4j 5 o índice BTree foi removido e substituído pelo Range.
4. **Limites da edição Community.** Constraints de existência (`IS NOT NULL`), de tipo e `NODE KEY`, além de usuários com papéis (só leitura), são exclusivos da Enterprise. A obrigatoriedade das propriedades fica a cargo da ingestão e dos testes. A proteção contra escrita nas consultas geradas pelo LLM é feita executando-as em transação de leitura (o banco recusa qualquer escrita).
5. **Versão fixa.** Neo4j 5.26.32 (LTS) com APOC e GDS 2.13.14, embutidos numa imagem Docker própria. Assim toda a equipe roda exatamente o mesmo banco, e o plugin não é baixado de novo a cada inicialização.
6. **Schema pré-definido e orientado ao domínio (R13).** Em vez de deixar o LLM inventar tipos, a extração só pode usar os 4 rótulos e as 5 relações abaixo. Isso reduz a variação entre artigos e deixa o Text-to-Cypher mais previsível, porque o mesmo arquivo (`neo4j/dominio.json`) alimenta os dois prompts.
7. **Português de ponta a ponta.** Índices fulltext com o analyzer `brazilian` e embeddings de 384 dimensões, decisão do grupo.

## Rótulos e relações do domínio

Fonte legível por código: [`neo4j/dominio.json`](../neo4j/dominio.json). Se mudar algo aqui, mude lá também (há teste conferindo a consistência do arquivo).

| Rótulo | Prefixo do id | Descrição | Exemplos |
|---|---|---|---|
| `Pessoa` | `pessoa` | Pessoa real ligada à história da computação: cientista, engenheiro, programador, fundador | Alan Turing, Dennis Ritchie, Grace Hopper |
| `Organizacao` | `organizacao` | Empresa, laboratório, universidade ou instituto | Bell Labs, IBM, Universidade de Cambridge |
| `Tecnologia` | `tecnologia` | Linguagem, sistema operacional, computador, máquina, algoritmo, protocolo ou padrão | C, Unix, ENIAC, TCP/IP |
| `Premio` | `premio` | Prêmio, medalha ou distinção recebida por uma pessoa | Prêmio Turing, Medalha Nacional de Tecnologia |

| Relação | De → Para | Descrição | Exemplo de pergunta multi-hop que ela habilita |
|---|---|---|---|
| `CRIOU` | `Pessoa` → `Tecnologia` ou `Organizacao` | Criou ou foi coautora da tecnologia, ou fundou a organização | "Quem criou a linguagem que influenciou o C++?" |
| `TRABALHOU_EM` | `Pessoa` → `Organizacao` | Trabalhou, pesquisou ou lecionou na organização | "Que prêmios receberam as pessoas que trabalharam no Bell Labs?" |
| `DESENVOLVIDA_EM` | `Tecnologia` → `Organizacao` | A tecnologia foi desenvolvida na organização | "Quais tecnologias do Bell Labs influenciaram outras linguagens?" |
| `INFLUENCIADA_POR` | `Tecnologia` → `Tecnologia` | A primeira foi influenciada pela segunda ou derivou dela | "Quais linguagens descendem, direta ou indiretamente, do BCPL?" |
| `RECEBEU` | `Pessoa` → `Premio` | A pessoa recebeu o prêmio | "Algum criador de uma linguagem que influenciou o C++ recebeu o Prêmio Turing?" |

A direção das relações é a proposta deste schema e precisa ser confirmada pelo grupo na issue #2.

### Ids canônicos

O id de cada nó segue a regra `<prefixo>:<nome normalizado>`: minúsculas, sem acento, `+` vira `_plus`, `#` vira `_sharp` e qualquer outro caractere que não seja letra ou número vira `_`.

| Nome | Id |
|---|---|
| Alan Turing | `pessoa:alan_turing` |
| C++ | `tecnologia:c_plus_plus` |
| Prêmio Turing | `premio:premio_turing` |
| Artigo "C++" da Wikipédia | `wikipedia:c_plus_plus` |
| Primeiro trecho desse artigo | `wikipedia:c_plus_plus#0` |

A implementação de referência dessa regra está em `id_canonico()`, em `tests/neo4j/conftest.py`.
