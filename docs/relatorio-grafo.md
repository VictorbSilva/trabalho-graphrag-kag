# Relatório do grafo carregado no Neo4j

Gerado em 16/11/2026 por `python -m src.banco.relatorio`, com o banco carregado a partir de `data/processado/curado` (31 artigos). Para atualizar, ingira os dados, rode o GDS e gere de novo (ver o cabeçalho de `src/banco/relatorio.py`).

## Resumo

| Documentos | Trechos | Entidades | Relações entre entidades | Comunidades |
|---|---|---|---|---|
| 31 | 1440 | 1295 | 736 | 719 |

## Por documento

| Documento | Trechos | Entidades mencionadas |
|---|---|---|
| Alan Kay (`alan_kay`) | 18 | 26 |
| Alan Turing (`alan_turing`) | 148 | 97 |
| ALGOL (`algol`) | 17 | 26 |
| Bell Labs (`bell_labs`) | 188 | 332 |
| Bjarne Stroustrup (`bjarne_stroustrup`) | 13 | 20 |
| Brendan Eich (`brendan_eich`) | 11 | 25 |
| Brian Kernighan (`brian_kernighan`) | 8 | 22 |
| C (linguagem de programação) (`c`) | 71 | 40 |
| C++ (`c_mais_mais`) | 132 | 47 |
| Dennis Ritchie (`dennis_ritchie`) | 34 | 45 |
| Guido van Rossum (`guido_van_rossum`) | 10 | 14 |
| James Gosling (`james_gosling`) | 18 | 21 |
| Java (linguagem de programação) (`java`) | 42 | 57 |
| JavaScript (`javascript`) | 114 | 104 |
| John McCarthy (`john_mccarthy`) | 7 | 7 |
| Ken Thompson (`ken_thompson`) | 2 | 8 |
| Linus Torvalds (`linus_torvalds`) | 32 | 35 |
| Linux (`linux`) | 94 | 133 |
| Lisp (`lisp`) | 56 | 63 |
| Netscape (`netscape`) | 20 | 31 |
| Niklaus Wirth (`niklaus_wirth`) | 10 | 18 |
| Oracle Corporation (`oracle_corporation`) | 5 | 6 |
| Organização Europeia para a Investigação Nuclear (`organizacao_europeia_para_a_investigacao_nuclear`) | 60 | 52 |
| Pascal (linguagem de programação) (`pascal`) | 34 | 51 |
| Prêmio Turing (`premio_turing`) | 2 | 5 |
| Python (`python`) | 97 | 77 |
| Simula (`simula`) | 20 | 24 |
| Smalltalk (`smalltalk`) | 13 | 21 |
| Sun Microsystems (`sun_microsystems`) | 41 | 47 |
| Tim Berners-Lee (`tim_berners_lee`) | 53 | 61 |
| Unix (`unix`) | 70 | 57 |

## Entidades por rótulo

| Rótulo | Entidades |
|---|---|
| `Tecnologia` | 632 |
| `Pessoa` | 333 |
| `Organizacao` | 283 |
| `Premio` | 47 |

## Relações por tipo

| Relação | Quantidade |
|---|---|
| `TRABALHOU_EM` | 187 |
| `CRIOU` | 185 |
| `DESENVOLVIDA_EM` | 148 |
| `INFLUENCIADA_POR` | 120 |
| `RECEBEU` | 96 |

## Qualidade da extração

- **Relações sem `source_chunk_ids`:** 0 (toda relação aponta para o trecho que a justifica).
- **Trechos que não mencionam nenhuma entidade:** 413 de 1440.
- **Entidades sem nenhuma relação de domínio:** 639 de 1295. Aparecem nos trechos, mas não se ligam a nenhuma outra entidade.
  - `Tecnologia`: 340 (ex.: AMD64, ActionScript Virtual Machine 2, Adobe Flash, Advanced Programming in the UNIX Environment, Ajax, AmigaOS 4, Amoeba, Amstrad, Apache Log4j, Apache Struts, Arc, Arch Linux, ...)
  - `Pessoa`: 148 (ex.: A. Michael Noll, Abraham Wald, Alan Mathison Turing, Alfred Y. Cho, Alick Glennie, Alonzo Church, Amos E. Joel Jr., Andreesen, Andrei Alexandrescu, Andrew Hodges, Antero Taivalsaari, Ari Lemmke, ...)
  - `Organizacao`: 146 (ex.: 3Com, AOL, AOL/Time Warner, AT&T Laboratories, AT&T Labs, AT&T Technologies, Academia Nacional de Ciências dos Estados Unidos, Academia Nacional de Engenharia, Academia Nacional de Engenharia dos Estados Unidos, Academia de Tecnologia da Finlândia, Adobe Systems, Air Canada, ...)
  - `Premio`: 5 (ex.: Emmy de Engenharia do Primetime, Emmy de Tecnologia e Engenharia, Grammy, Grammy Técnico, Prêmios Emmy)
- **Prováveis duplicatas** (mesmo nome normalizado, ou o nome de uma é apelido da outra): 85:
  - Adobe Systems / Macromedia (`Organizacao`)
  - Alcatel-Lucent Bell Labs / Bell Labs (`Organizacao`)
  - American National Standards Institute / ANSI (`Organizacao`)
  - American Telephone and Telegraph Company / AT&T (`Organizacao`)
  - Apple / Apple Inc. (`Organizacao`)
  - AT&T / Laboratórios Bell da AT&T (`Organizacao`)
  - AT&T Technologies / Western Electric (`Organizacao`)
  - Bell Laboratories / Bell Labs (`Organizacao`)
  - Bell Labs / Bell Labs Computing Science Research Center (`Organizacao`)
  - Bell Labs / Bell System (`Organizacao`)
  - Bell Labs / Nokia Bell Labs (`Organizacao`)
  - Centrum Wiskunde & Informatica / CWI (`Organizacao`)
  - CERN / Conselho Europeu para Pesquisa Nuclear (`Organizacao`)
  - CERN / Organização Europeia para a Investigação Nuclear (`Organizacao`)
  - CNRI / Corporation for National Research Initiatives (`Organizacao`)
  - CWI / Instituto de Pesquisa Nacional para Matemática e Ciência da Computação (`Organizacao`)
  - DEC / Digital Equipament Corporation (`Organizacao`)
  - Escola de Código e Cifra do Governo / GC&CS (`Organizacao`)
  - Escola de Código e Cifras do Governo / GC&CS (`Organizacao`)
  - Free Software Foundation / FSF (`Organizacao`)
  - GCHQ / Sede de Comunicações do Governo (`Organizacao`)
  - GE / General Electric (`Organizacao`)
  - GNU / Projeto GNU (`Organizacao`)
  - Hewlett-Packard / HP (`Organizacao`)
  - IEEE / Instituto de Engenheiros Eletricistas e Eletrônicos (`Organizacao`)
  - Instituto de Tecnologia de Massachusetts / MIT (`Organizacao`)
  - International Organization for Standardization / ISO (`Organizacao`)
  - Laboratório Nacional de Física / NPL (`Organizacao`)
  - Laboratórios Bell / Laboratórios Bell da AT&T (`Organizacao`)
  - Lucent / Lucent Technologies (`Organizacao`)
  - Massachusetts Institute of Technology / MIT (`Organizacao`)
  - Mosaic Communications / Netscape (`Organizacao`)
  - Mosaic Communications / Netscape Communications (`Organizacao`)
  - Netscape / Netscape Communications (`Organizacao`)
  - Netscape / Netscape Communications Corporation (`Organizacao`)
  - Sun / Sun Microsystems (`Organizacao`)
  - Alan Mathison Turing / Alan Turing (`Pessoa`)
  - Arnold Murray / Murray (`Pessoa`)
  - Brendan Eich / Eich (`Pessoa`)
  - Glapa / Martin J. Glapa (`Pessoa`)
  - Guido / Guido van Rossum (`Pessoa`)
  - Linus Torvalds / Torvalds (`Pessoa`)
  - Peter J. Weinberger / Peter Weinberger (`Pessoa`)
  - Nobel de Física / Prêmio Nobel de Física (`Premio`)
  - ALGOL / ALGOL 58 (`Tecnologia`)
  - ALGOL / ALGOL 60 (`Tecnologia`)
  - ALGOL / ALGOL 68 (`Tecnologia`)
  - ANSI C / C (`Tecnologia`)
  - B / Linguagem B (`Tecnologia`)
  - Berkeley Software Distribution / BSD (`Tecnologia`)
  - Blit / Teletype/AT&T 5620 Dot Mapped Display (`Tecnologia`)
  - Bomba / Bomba eletromecânica (`Tecnologia`)
  - C / Linguagem C (`Tecnologia`)
  - C++ / C with Classes (`Tecnologia`)
  - Complex Number Calculator / Modelo I (`Tecnologia`)
  - Delphi / Object Pascal (`Tecnologia`)
  - ECMA-262 / ECMAScript (`Tecnologia`)
  - Enigma / Máquina Enigma (`Tecnologia`)
  - Firefox / Mozilla Firefox (`Tecnologia`)
  - freax / Linux (`Tecnologia`)
  - GCC / GNU Compiler Collection (`Tecnologia`)
  - GNU/Linux / Linux (`Tecnologia`)
  - Grande Colisionador de Hadrões / LHC (`Tecnologia`)
  - ISO 7185 / ISO / IEC 7185 (`Tecnologia`)
  - Java Virtual Machine / JVM (`Tecnologia`)
  - JavaScript / LiveScript (`Tecnologia`)
  - JavaScript / Mocha (`Tecnologia`)
  - Large Hadron Collider / LHC (`Tecnologia`)
  - LEIR / Low Energy Ion Ring (`Tecnologia`)
  - máquina de Turing / máquina universal de Turing (`Tecnologia`)
  - máquina universal de Turing / máquinas de Turing (`Tecnologia`)
  - Microsoft Windows / Windows (`Tecnologia`)
  - Mosaic Netscape / Netscape Navigator (`Tecnologia`)
  - Netscape / Netscape Navigator (`Tecnologia`)
  - PS Booster / PSB (`Tecnologia`)
  - Python / Python 2.0 (`Tecnologia`)
  - Python / Python 2.6 (`Tecnologia`)
  - Python / Python 3 (`Tecnologia`)
  - Python / Python 3.0 (`Tecnologia`)
  - Python 3 / Python 3.0 (`Tecnologia`)
  - sistema celular de terceira geração baseado em W-CDMA / W-CDMA (`Tecnologia`)
  - Solaris / SunOS (`Tecnologia`)
  - Standard Template Library / STL (`Tecnologia`)
  - UCSD / UCSD p-System (`Tecnologia`)
  - Unics / Unix (`Tecnologia`)
- **Nomes contidos um no outro:** 187 pares do mesmo tipo. Muitos são versões ou variantes legítimas (ex.: Java e Java SE), mas alguns podem ser a mesma entidade:
  - Academia Nacional de Engenharia / Academia Nacional de Engenharia dos Estados Unidos (`Organizacao`)
  - Alcatel / Alcatel-Lucent (`Organizacao`)
  - Alcatel / Alcatel-Lucent Bell Labs (`Organizacao`)
  - Alcatel / Alcatel Research and Innovation (`Organizacao`)
  - Alcatel-Lucent / Alcatel-Lucent Bell Labs (`Organizacao`)
  - Alcatel-Lucent / Lucent (`Organizacao`)
  - Alcatel-Lucent Bell Labs / Lucent (`Organizacao`)
  - American Bell Telephone Company / Bell Telephone Company (`Organizacao`)
  - Apple / Apple Computer (`Organizacao`)
  - AT&T Bell Laboratories / AT&T Laboratories (`Organizacao`)
  - AT&T Bell Laboratories / Bell Laboratories (`Organizacao`)
  - Bell Laboratories / Lucent Bell Laboratories (`Organizacao`)
  - ... e mais 175 pares

## Entidades mais importantes (PageRank)

| # | Entidade | Rótulo | PageRank |
|---|---|---|---|
| 1 | Bell Labs | `Organizacao` | 27.817 |
| 2 | Alan Turing | `Pessoa` | 13.051 |
| 3 | Tim Berners-Lee | `Pessoa` | 11.811 |
| 4 | Sun Microsystems | `Organizacao` | 10.195 |
| 5 | Bell Laboratories | `Organizacao` | 6.965 |

## Comunidades (Louvain)

719 comunidades, 80 delas com mais de uma entidade (as entidades sem relação ficam sozinhas). As maiores, com as entidades de maior PageRank de cada uma:

| Comunidade | Entidades | Principais |
|---|---|---|
| 210 | 74 | Bell Labs, Medalha Nacional de Tecnologia, laser a gás, Blit, AMPL |
| 262 | 46 | Dennis Ritchie, Unix, Ken Thompson, Prêmio Turing, BSD |
| 54 | 44 | Alan Turing, Bletchley Park, Bomba, Hut 8, Laboratório Nacional de Física |
| 1040 | 40 | Tim Berners-Lee, CERN, W3C, Enquire, World Wide Web |
| 467 | 35 | C++, ALGOL, C, Java, Burroughs |
| 660 | 35 | Sun Microsystems, James Gosling, Andy Bechtolsheim, SunOS, Scott McNealy |
| 744 | 35 | Brendan Eich, JavaScript, Netscape, Google, Brave Software |
| 252 | 33 | Bell Laboratories, Nobel de Física, Transistor, John Bardeen, Prêmio Nobel de Física |

## Como conferir no Neo4j Browser

```cypher
MATCH (d:Document) RETURN count(d);
MATCH (e:Entity) UNWIND [r IN labels(e) WHERE r <> 'Entity'] AS rotulo RETURN rotulo, count(*);
MATCH (:Entity)-[r]->(:Entity) RETURN type(r), count(*);
MATCH (:Entity)-[r]->(:Entity) WHERE r.source_chunk_ids IS NULL OR size(r.source_chunk_ids) = 0 RETURN count(r);
MATCH (e:Entity) RETURN e.name, e.pagerank ORDER BY e.pagerank DESC LIMIT 5;
```
