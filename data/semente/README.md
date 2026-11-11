# Grafo semente (anotado à mão)

Grafo pequeno, no mesmo formato que o pipeline vai entregar (ver `arquivo_por_artigo` em [`neo4j/dominio.json`](../../neo4j/dominio.json)). Serve para a recuperação e a interface trabalharem antes de o pipeline ficar pronto, e para os testes do banco.

| Arquivo | Artigo | Trechos | Entidades | Relações |
|---|---|---|---|---|
| `c_linguagem_de_programacao.json` | C (linguagem de programação) | 3 | 9 | 6 |
| `c_plus_plus.json` | C++ | 2 | 7 | 5 |
| `dennis_ritchie.json` | Dennis Ritchie | 5 | 9 | 11 |
| `ken_thompson.json` | Ken Thompson | 2 | 6 | 5 |

Depois da ingestão, as entidades repetidas entre artigos viram um nó só (mesmo id canônico): ao todo são **13 entidades** (3 `Pessoa`, 2 `Organizacao`, 6 `Tecnologia`, 2 `Premio`) e **19 relações** distintas, cobrindo as 5 relações do domínio.

Exemplo de caminho de 3 saltos entre artigos diferentes: C++ `INFLUENCIADA_POR` C, que Dennis Ritchie `CRIOU`, e Dennis Ritchie `RECEBEU` o Prêmio Turing.

## Como foi anotado

- **Trechos:** parágrafos copiados sem alteração dos artigos, escolhidos por conterem os fatos anotados. Os trechos de cada arquivo não são parágrafos vizinhos no artigo original.
- **Entidades e relações:** anotadas à mão. Toda relação aponta, em `chunk_id`, para um trecho do mesmo arquivo cujo texto sustenta o fato.
- **Ids:** seguem a regra de id canônico de `neo4j/dominio.json`.
- **Sem embedding:** quem calcula os embeddings é o ingestor.

Os testes em `tests/neo4j/test_semente.py` conferem o formato, a cobertura do domínio, o caminho de 3 saltos e a ingestão no banco.

## Créditos e licença

Os textos dos trechos são da [Wikipédia em português](https://pt.wikipedia.org), copiados em 11/11/2026 e distribuídos sob a licença [Creative Commons Atribuição-CompartilhaIgual 4.0 (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/deed.pt-br). Os autores são os editores de cada artigo, listados no histórico de cada página. Por causa do CompartilhaIgual, os arquivos desta pasta são distribuídos sob a mesma licença.

| Artigo | Versão usada |
|---|---|
| [C (linguagem de programação)](https://pt.wikipedia.org/wiki/C_(linguagem_de_programa%C3%A7%C3%A3o)) | [revisão 73266139](https://pt.wikipedia.org/w/index.php?oldid=73266139), de 22/10/2026 |
| [C++](https://pt.wikipedia.org/wiki/C%2B%2B) | [revisão 73129050](https://pt.wikipedia.org/w/index.php?oldid=73129050), de 05/10/2026 |
| [Dennis Ritchie](https://pt.wikipedia.org/wiki/Dennis_Ritchie) | [revisão 73232970](https://pt.wikipedia.org/w/index.php?oldid=73232970), de 17/10/2026 |
| [Ken Thompson](https://pt.wikipedia.org/wiki/Ken_Thompson) | [revisão 73064383](https://pt.wikipedia.org/w/index.php?oldid=73064383), de 27/09/2026 |
