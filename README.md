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

`python -m pytest` roda a suíte inteira (banco, pipeline, recuperação e API). Os testes que dependem de serviço externo têm marcador e podem ser rodados à parte:

| Comando | O que roda |
|---|---|
| `python -m pytest -m neo4j` | só os testes que precisam do Neo4j no ar (tudo em `tests/neo4j/`) |
| `python -m pytest -m llm` | só os testes que precisam de chave de LLM |
| `python -m pytest -m "not neo4j and not llm"` | só os que rodam em qualquer máquina (é o que o CI roda) |

Se o Neo4j estiver fora do ar, os testes do banco aparecem como pulados, com o motivo no resumo. Para exigir o banco, rode com `EXIGIR_NEO4J=1`. Teste novo que chama um LLM deve levar `@pytest.mark.llm`. O CI do GitHub ([.github/workflows/testes.yml](.github/workflows/testes.yml)) roda a cada push na `main` e em todo pull request.

API (FastAPI), com o ambiente virtual ativo:

```bash
uvicorn src.api.app:app --reload --port 8000
```

- `GET http://localhost:8000/saude` responde se a API está no ar.
- `POST http://localhost:8000/perguntar` recebe `{"pergunta": "...", "modo": "graphrag"}` (`modo` é `graphrag` ou `vetorial`) e devolve o objeto do contrato da resposta. Documentação interativa em http://localhost:8000/docs.
- Por padrão a API devolve o JSON de exemplo do contrato (`data/exemplo_resposta.json`), sem banco nem LLM. Com `API_FONTE=recuperacao` e `API_RESPONDER=modulo:funcao` no `.env`, ela chama a recuperação de verdade. As outras variáveis (`API_TIMEOUT_S`, `API_CORS_ORIGENS`) estão no `.env.example`.

```bash
curl -X POST http://localhost:8000/perguntar -H "Content-Type: application/json" -d "{\"pergunta\": \"Quem criou o C?\", \"modo\": \"graphrag\"}"
```

Detalhes do banco em [neo4j/README.md](neo4j/README.md) e do modelo do grafo em [docs/modelo-do-grafo.md](docs/modelo-do-grafo.md).

## Fluxo de trabalho

- Uma branch por tarefa e pull request revisado por pelo menos um colega antes do merge.
- Cada módulo vem com os próprios testes em `tests/<módulo>/`.
- Todo código ou exemplo de terceiros é creditado.
