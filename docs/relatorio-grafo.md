# Relatório do grafo carregado no Neo4j

Gerado em 15/11/2026 por `python -m src.banco.relatorio`, com o banco carregado a partir de `data/processado/extraido` (5 artigos). Para atualizar, ingira os dados, rode o GDS e gere de novo (ver o cabeçalho de `src/banco/relatorio.py`).

## Resumo

| Documentos | Trechos | Entidades | Relações entre entidades | Comunidades |
|---|---|---|---|---|
| 5 | 247 | 49 | 52 | 16 |

## Por documento

| Documento | Trechos | Entidades mencionadas |
|---|---|---|
| Brian Kernighan (`brian_kernighan`) | 8 | 23 |
| C (linguagem de programação) (`c`) | 71 | 14 |
| C++ (`c_mais_mais`) | 132 | 11 |
| Dennis Ritchie (`dennis_ritchie`) | 34 | 15 |
| Ken Thompson (`ken_thompson`) | 2 | 8 |

## Entidades por rótulo

| Rótulo | Entidades |
|---|---|
| `Tecnologia` | 26 |
| `Pessoa` | 12 |
| `Organizacao` | 8 |
| `Premio` | 3 |

## Relações por tipo

| Relação | Quantidade |
|---|---|
| `CRIOU` | 19 |
| `INFLUENCIADA_POR` | 12 |
| `TRABALHOU_EM` | 10 |
| `RECEBEU` | 6 |
| `DESENVOLVIDA_EM` | 5 |

## Qualidade da extração

- **Relações sem `source_chunk_ids`:** 0 (toda relação aponta para o trecho que a justifica).
- **Trechos que não mencionam nenhuma entidade:** 217 de 247.
- **Entidades sem nenhuma relação de domínio:** 11. Aparecem nos trechos, mas não se ligam a nenhuma outra entidade:
  - Universidade Harvard (`Organizacao`)
  - Universidade de Toronto (`Organizacao`)
  - Alfred V. Aho (`Pessoa`)
  - Niklaus Wirth (`Pessoa`)
  - Rob Pike (`Pessoa`)
  - Stephen C. Johnson (`Pessoa`)
  - Assembly (`Tecnologia`)
  - ISO 7185 (`Tecnologia`)
  - PDP-11 (`Tecnologia`)
  - PDP-7 (`Tecnologia`)
  - Pascal (`Tecnologia`)
- **Possíveis duplicatas** (mesmo tipo, nomes parecidos): 4:
  - AT&T Bell Labs / Bell Labs (`Organizacao`): um nome contém o outro
  - Bell Labs / Bell Labs Computing Science Research Center (`Organizacao`): o nome de uma é apelido da outra
  - Alfred Aho / Alfred V. Aho (`Pessoa`): um nome contém o outro
  - Johnson / Stephen C. Johnson (`Pessoa`): o nome de uma é apelido da outra

## Entidades mais importantes (PageRank)

| # | Entidade | Rótulo | PageRank |
|---|---|---|---|
| 1 | Brian Kernighan | `Pessoa` | 3.642 |
| 2 | C++ | `Tecnologia` | 3.335 |
| 3 | Dennis Ritchie | `Pessoa` | 3.173 |
| 4 | Ken Thompson | `Pessoa` | 2.680 |
| 5 | Bell Labs | `Organizacao` | 2.106 |

## Comunidades (Louvain)

16 comunidades. As maiores, com as entidades de maior PageRank de cada uma:

| Comunidade | Entidades | Principais |
|---|---|---|
| 6 | 12 | Brian Kernighan, AWK, eqn, m4, Lorinda Cherry |
| 37 | 10 | C++, Bell Labs, Unix, Bjarne Stroustrup, BCPL |
| 47 | 8 | Ken Thompson, Bell Labs Computing Science Research Center, Multics, Medalha IEEE Richard W. Hamming, Medalha Nacional de Tecnologia e Inovação |
| 21 | 6 | Dennis Ritchie, C, B, AT&T Bell Labs, Java |
| 34 | 2 | Johnson, Portable C Compiler |
| 2 | 1 | Universidade de Toronto |
| 5 | 1 | Alfred V. Aho |
| 27 | 1 | Niklaus Wirth |

## Como conferir no Neo4j Browser

```cypher
MATCH (d:Document) RETURN count(d);
MATCH (e:Entity) UNWIND [r IN labels(e) WHERE r <> 'Entity'] AS rotulo RETURN rotulo, count(*);
MATCH (:Entity)-[r]->(:Entity) RETURN type(r), count(*);
MATCH (:Entity)-[r]->(:Entity) WHERE r.source_chunk_ids IS NULL OR size(r.source_chunk_ids) = 0 RETURN count(r);
MATCH (e:Entity) RETURN e.name, e.pagerank ORDER BY e.pagerank DESC LIMIT 5;
```
