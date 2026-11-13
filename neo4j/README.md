# Banco de dados (Neo4j)

Neo4j 5.26 LTS (Community) com os plugins APOC e Graph Data Science, rodando no Docker. O modelo do grafo está explicado em [docs/modelo-do-grafo.md](../docs/modelo-do-grafo.md).

## Subir o banco

Pré-requisito: Docker Desktop aberto.

```bash
cp .env.example .env        # depois edite o .env e troque a senha
docker compose up -d
```

Na primeira vez demora alguns minutos: o Docker constrói a imagem a partir do [Dockerfile](Dockerfile), baixando o Neo4j e o GDS uma única vez. Nas próximas, o banco sobe em menos de um minuto. O serviço `neo4j-schema` espera o banco ficar pronto, aplica constraints e índices e termina sozinho. Para ver o resultado:

```bash
docker compose logs neo4j-schema
```

- Neo4j Browser: http://localhost:7474 (usuário `neo4j`, senha do `.env`)
- Bolt para os drivers: `bolt://localhost:7687`

## Já tinha subido o banco antes de 11/11? Recrie os índices

Na issue #3 os índices mudaram: os vetoriais passaram de 1536 para **384 dimensões** e os fulltext passaram a usar o analyzer **`brazilian`**. Como o schema usa `IF NOT EXISTS`, um banco que já existia continua com os índices antigos. Escolha um dos caminhos:

- **Banco sem dados que importem** (o caso de quase todo mundo agora): apague e suba de novo.

  ```bash
  docker compose down -v
  docker compose up -d
  ```

- **Banco com dados que você quer manter:** recrie só os índices fulltext e vetoriais (constraints, índices Range e nós ficam como estão).

  ```bash
  docker compose run --rm neo4j-recriar-indices
  ```

  Embeddings gravados com outra dimensão não entram no índice novo: rode a ingestão de novo depois.

Para conferir, `SHOW VECTOR INDEXES` no Browser deve mostrar 384 nos dois índices, e `python -m pytest` deve passar.

## Comandos do dia a dia

| O que | Comando |
|---|---|
| Reaplicar o schema (é idempotente) | `docker compose up neo4j-schema` |
| Recriar índices fulltext e vetoriais | `docker compose run --rm neo4j-recriar-indices` |
| Rodar PageRank e Louvain depois da ingestão | `docker compose run --rm neo4j-gds` |
| Parar o banco (mantém os dados) | `docker compose down` |
| Apagar tudo e começar do zero | `docker compose down -v` |
| Testes do banco | `python -m pytest` |

## Testes

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (no Linux/Mac: source .venv/bin/activate)
pip install -r requirements-dev.txt
python -m pytest
```

Os testes conferem constraints, índices, plugins, o modelo de ingestão (idempotência e resolução de entidades), as consultas de referência, os algoritmos do GDS e o bloqueio de escrita em transações de leitura. Eles só criam nós com id começando em `teste::` e apagam tudo no final.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `Dockerfile` | Imagem do Neo4j com APOC e GDS (versão do GDS fixada e conferida por checksum) |
| `dominio.json` | Rótulos, relações (com direção), regra do id canônico e formato do arquivo por artigo. Fonte única para os prompts de extração e de Text-to-Cypher |
| `schema/` | Constraints e índices, aplicados automaticamente no `docker compose up` |
| `manutencao/` | Scripts de manutenção, como a recriação de índices |
| `gds/` | Projeção, PageRank, Louvain e limpeza, rodados com `docker compose run --rm neo4j-gds` |
| `consultas/exemplos.cypher` | Consultas de referência: fulltext, vetorial, híbrida multi-hop, caminho mais curto, procedência, comunidades |
| `consultas/ingestao_modelo.cypher` | Modelo de ingestão com `MERGE` que respeita as constraints (contrato com o pipeline Text-to-Graph) |

## Problemas comuns

- **Erro no build ao baixar o GDS** (`sha256sum: WARNING` ou falha do `wget`): problema de rede na hora do download. Rode `docker compose up -d --build` de novo.
- **Mudou o modelo de embeddings:** ajuste `vector.dimensions` em `schema/03_vector_indexes.cypher` e `embedding.dimensoes` em `dominio.json`, e depois rode `docker compose run --rm neo4j-recriar-indices`.
- **Porta 7474 ou 7687 ocupada:** mude `NEO4J_HTTP_PORT` / `NEO4J_BOLT_PORT` no `.env`.
