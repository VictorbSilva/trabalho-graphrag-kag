# Trabalho GraphRAG e KAG

Sistema de perguntas e respostas sobre um grafo de conhecimento no Neo4j, construído a partir de documentos não estruturados. As respostas citam os caminhos do grafo usados e trazem um nível de confiança.

Tendências em Ciência da Computação, Prof. Ricardo Roberto de Lima, 2026.

## Equipe

| Integrante | Pilar |
|---|---|
| Victor | Recuperação híbrida, multi-hop e backend |
| Nicolas | Modelagem LPG no Neo4j e algoritmos de grafo |
| Patrick | Pipeline Text-to-Graph, avaliação e testes |
| Gabriel | Interface e visualização |

## Estrutura

```
docker-compose.yml     Neo4j 5.26 + APOC + GDS
neo4j/
  Dockerfile           imagem do Neo4j com os plugins já instalados
  schema/              constraints e índices (aplicados no docker compose up)
  gds/                 PageRank e Louvain
  consultas/           modelo de ingestão e consultas de referência
docs/                  documentação (modelo do grafo)
tests/
  neo4j/               testes do banco
```

## Como rodar

Pré-requisitos: Docker Desktop e Python 3.10+.

```bash
cp .env.example .env          # no Windows: copy .env.example .env  (depois troque a senha)
docker compose up -d          # sobe o Neo4j e aplica o schema
```

Neo4j Browser: http://localhost:7474 (usuário `neo4j`, senha do `.env`).

Testes:

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```

Detalhes do banco em [neo4j/README.md](neo4j/README.md) e do modelo do grafo em [docs/modelo-do-grafo.md](docs/modelo-do-grafo.md).

## Fluxo de trabalho

- Uma branch por tarefa e pull request revisado por pelo menos um colega antes do merge.
- Cada módulo vem com os próprios testes em `tests/<módulo>/`.
- Todo código ou exemplo de terceiros é creditado.
