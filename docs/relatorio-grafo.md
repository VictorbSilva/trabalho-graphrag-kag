# Relatório do grafo carregado no Neo4j

Gerado em 15/11/2026 por `python -m src.banco.relatorio`, com o banco carregado a partir de `data/processado/extraido` (17 artigos). Para atualizar, ingira os dados, rode o GDS e gere de novo (ver o cabeçalho de `src/banco/relatorio.py`).

## Resumo

| Documentos | Trechos | Entidades | Relações entre entidades | Comunidades |
|---|---|---|---|---|
| 17 | 567 | 467 | 259 | 265 |

## Por documento

| Documento | Trechos | Entidades mencionadas |
|---|---|---|
| Alan Kay (`alan_kay`) | 18 | 26 |
| Brian Kernighan (`brian_kernighan`) | 8 | 23 |
| C (linguagem de programação) (`c`) | 71 | 41 |
| C++ (`c_mais_mais`) | 132 | 47 |
| Dennis Ritchie (`dennis_ritchie`) | 34 | 45 |
| Guido van Rossum (`guido_van_rossum`) | 10 | 14 |
| James Gosling (`james_gosling`) | 18 | 21 |
| Java (linguagem de programação) (`java`) | 42 | 57 |
| John McCarthy (`john_mccarthy`) | 7 | 7 |
| Ken Thompson (`ken_thompson`) | 2 | 8 |
| Linus Torvalds (`linus_torvalds`) | 32 | 35 |
| Lisp (`lisp`) | 56 | 63 |
| Niklaus Wirth (`niklaus_wirth`) | 10 | 18 |
| Simula (`simula`) | 20 | 24 |
| Smalltalk (`smalltalk`) | 13 | 21 |
| Sun Microsystems (`sun_microsystems`) | 41 | 47 |
| Tim Berners-Lee (`tim_berners_lee`) | 53 | 61 |

## Entidades por rótulo

| Rótulo | Entidades |
|---|---|
| `Tecnologia` | 237 |
| `Organizacao` | 138 |
| `Pessoa` | 64 |
| `Premio` | 28 |

## Relações por tipo

| Relação | Quantidade |
|---|---|
| `CRIOU` | 73 |
| `TRABALHOU_EM` | 59 |
| `DESENVOLVIDA_EM` | 49 |
| `RECEBEU` | 42 |
| `INFLUENCIADA_POR` | 36 |

## Qualidade da extração

- **Relações sem `source_chunk_ids`:** 0 (toda relação aponta para o trecho que a justifica).
- **Trechos que não mencionam nenhuma entidade:** 228 de 567.
- **Entidades sem nenhuma relação de domínio:** 238 de 467. Aparecem nos trechos, mas não se ligam a nenhuma outra entidade.
  - `Tecnologia`: 136 (ex.: ABC, AMD64, Advanced Programming in the UNIX Environment, Apache Log4j, Apache Struts, Arc, Assembly, AutoCAD, BASIC, Blade server, BlueJ, Boost, ...)
  - `Organizacao`: 72 (ex.: 3Com, AT&T, Academia Nacional de Ciências dos Estados Unidos, Academia Nacional de Engenharia dos Estados Unidos, Academia de Tecnologia da Finlândia, Apache Software Foundation, Apple, Association for Computing Machinery, AutoDesk, Boost.org, Borland, CSAIL, ...)
  - `Pessoa`: 30 (ex.: Alfred V. Aho, Andrei Alexandrescu, Ari Lemmke, Bonnie MacBird, Conway Berners-Lee, Dan Weinreb, Doug McIlroy, Eric S., Eric S. Raymond, Herb Sutter, James Reeds, Jon Hall, ...)
- **Prováveis duplicatas** (mesmo nome normalizado, ou o nome de uma é apelido da outra): 9:
  - American National Standards Institute / ANSI (`Organizacao`)
  - Bell Labs / Bell Labs Computing Science Research Center (`Organizacao`)
  - Hewlett-Packard / HP (`Organizacao`)
  - Instituto de Tecnologia de Massachusetts / MIT (`Organizacao`)
  - International Organization for Standardization / ISO (`Organizacao`)
  - C++ / C with Classes (`Tecnologia`)
  - GCC / GNU Compiler Collection (`Tecnologia`)
  - Java Virtual Machine / JVM (`Tecnologia`)
  - Standard Template Library / STL (`Tecnologia`)
- **Nomes contidos um no outro:** 53 pares do mesmo tipo. Muitos são versões ou variantes legítimas (ex.: Java e Java SE), mas alguns podem ser a mesma entidade:
  - Apple / Apple Computer (`Organizacao`)
  - AT&T Bell Labs / Bell Labs (`Organizacao`)
  - IEEE / IEEE Computer Society (`Organizacao`)
  - Oracle / Oracle Corporation (`Organizacao`)
  - Proton / Proton Foundation (`Organizacao`)
  - Xerox / Xerox PARC (`Organizacao`)
  - Alfred Aho / Alfred V. Aho (`Pessoa`)
  - Eric S. / Eric S. Raymond (`Pessoa`)
  - Medalha IEEE Richard W. Hamming / Medalha Richard W. Hamming (`Premio`)
  - Medalha Nacional de Tecnologia e Inovação / Medalha Nacional de Tecnologia e Inovação de 1998 (`Premio`)
  - Prêmio Turing / Prêmio Turing 2001 A.M. (`Premio`)
  - Advanced Programming in the UNIX Environment / Unix (`Tecnologia`)
  - ... e mais 41 pares

## Entidades mais importantes (PageRank)

| # | Entidade | Rótulo | PageRank |
|---|---|---|---|
| 1 | Tim Berners-Lee | `Pessoa` | 11.243 |
| 2 | Sun Microsystems | `Organizacao` | 10.513 |
| 3 | Linus Torvalds | `Pessoa` | 5.985 |
| 4 | Alan Kay | `Pessoa` | 5.947 |
| 5 | James Gosling | `Pessoa` | 5.587 |

## Comunidades (Louvain)

265 comunidades, 27 delas com mais de uma entidade (as entidades sem relação ficam sozinhas). As maiores, com as entidades de maior PageRank de cada uma:

| Comunidade | Entidades | Principais |
|---|---|---|
| 450 | 30 | Tim Berners-Lee, CERN, W3C, ENQUIRE, World Wide Web |
| 84 | 25 | C++, C, Java, Ole-Johan Dahl, Simula |
| 108 | 23 | Sun Microsystems, Andy Bechtolsheim, Scott McNealy, Kaelia, Bill Joy |
| 190 | 21 | James Gosling, Guido van Rossum, Google, NeWS, Centrum Wiskunde & Informatica |
| 250 | 21 | Niklaus Wirth, John McCarthy, LISP 1.5, MIT, Lisp |
| 52 | 18 | Dennis Ritchie, Ken Thompson, Bell Labs, Prêmio Turing, Unix |
| 16 | 16 | Alan Kay, Xerox PARC, Alto, Smalltalk, Chuck Thacker |
| 268 | 16 | Linus Torvalds, Linux, freax, Prêmio de Tecnologia do Milênio, Exército da Finlândia |

## Como conferir no Neo4j Browser

```cypher
MATCH (d:Document) RETURN count(d);
MATCH (e:Entity) UNWIND [r IN labels(e) WHERE r <> 'Entity'] AS rotulo RETURN rotulo, count(*);
MATCH (:Entity)-[r]->(:Entity) RETURN type(r), count(*);
MATCH (:Entity)-[r]->(:Entity) WHERE r.source_chunk_ids IS NULL OR size(r.source_chunk_ids) = 0 RETURN count(r);
MATCH (e:Entity) RETURN e.name, e.pagerank ORDER BY e.pagerank DESC LIMIT 5;
```
