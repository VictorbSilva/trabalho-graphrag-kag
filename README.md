# Trabalho GraphRAG e KAG

Sistema de perguntas e respostas sobre um grafo de conhecimento no Neo4j, construído a partir de documentos não estruturados. As respostas citam os caminhos do grafo usados e trazem um nível de confiança.

Tendências em Ciência da Computação, Prof. Ricardo Roberto de Lima, 2026.

## Domínio

**História da computação.** O grafo é construído a partir de cerca de 30 artigos da Wikipédia em português (licença CC BY-SA) sobre pessoas, organizações, tecnologias e prêmios da computação. Exemplo de pergunta multi-hop: *"Algum criador de uma linguagem que influenciou o C++ recebeu o Prêmio Turing?"*

| Rótulos | Relações |
|---|---|
| `Pessoa`, `Organizacao`, `Tecnologia`, `Premio` | `CRIOU`, `TRABALHOU_EM`, `DESENVOLVIDA_EM`, `INFLUENCIADA_POR`, `RECEBEU` |

Schema completo em [docs/modelo-do-grafo.md](docs/modelo-do-grafo.md) e, em formato legível por código, em [neo4j/dominio.json](neo4j/dominio.json).

## Equipe

| Integrante | Frente |
|---|---|
| Victor | Contratos, recuperação híbrida, multi-hop e avaliação comparativa |
| Nicolas | Banco Neo4j (modelagem, ingestão e algoritmos de grafo) e artigo |
| Patrick | Pipeline Text-to-Graph (dataset, extração e resolução de entidades) |
| Gabriel | Interface, agente Mentor e apresentação |
| Pedro | API, perguntas de avaliação e entrega (README, testes, demo) |

O backlog com as issues de cada um está no quadro [Backlog GraphRAG e KAG](https://github.com/users/VictorbSilva/projects/4).

## Estrutura

```
.github/workflows/     CI: roda os testes sem serviço externo a cada push na main e em todo pull request
docker-compose.yml     Neo4j 5.26 + APOC + GDS
requirements-dev.txt   dependências do projeto (inclui requirements-api.txt)
requirements-interface.txt  dependências da interface
data/
  bruto/               texto puro dos artigos da Wikipédia e manifesto.json (título, URL e revisão)
  processado/          chunks/ e extraido/ (um JSON por artigo), saída do pipeline Text-to-Graph
  semente/             grafo semente anotado à mão (4 artigos)
  avaliacao/           as 15 perguntas com gabarito, a classificação manual e resultados/respostas.json
  exemplo_resposta.json  JSON de exemplo do contrato da resposta
docs/
  artigo/              artigo técnico (artigo.tex, artigo.pdf e referências)
  modelo-do-grafo.md   modelo do grafo
  confianca.md         como o nível de confiança é calculado
  avaliacao-resultados.md, avaliacao-planilha.md  resultados da avaliação e planilha de classificação
  relatorio-grafo.md   relatório do grafo carregado (PageRank e comunidades)
  mentor.md            agente Mentor
neo4j/
  Dockerfile           imagem do Neo4j com os plugins já instalados
  dominio.json         rótulos, relações e regra de ids do domínio
  schema/              constraints e índices (aplicados no docker compose up)
  gds/                 PageRank e Louvain
  consultas/           modelo de ingestão e consultas de referência
  manutencao/          recriação dos índices
src/
  contrato.py          contrato da resposta (Pydantic)
  pipeline/            Text-to-Graph: download, chunking, extração com o Groq ou o Gemini e resolução de entidades
  banco/               ingestor e relatório do grafo
  recuperacao/         embeddings, busca vetorial, Text-to-Cypher, multi-hop, confiança e responder()
  api/                 API FastAPI (/saude e /perguntar)
  interface/           interface Streamlit
  avaliacao/           comparação RAG vetorial vs GraphRAG
  mentor/              agente Mentor (chat no terminal)
tests/                 uma pasta por módulo: api, avaliacao, contrato, mentor, neo4j, pipeline, recuperacao
```

## Como rodar

Passo a passo do zero até uma pergunta respondida na interface. Os comandos são para o PowerShell do Windows; quando o comando muda no Linux ou no Mac, ele aparece logo abaixo. O que está marcado como *(não testado)* não foi executado no teste do zero deste README.

Para só ver a interface, sem banco nem LLM: deixe `API_FONTE=exemplo` e pule os passos 5 e 6.

### 1. Pré-requisitos

- [Git](https://git-scm.com).
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e **aberto** (no Windows, espere o Docker Desktop mostrar *Engine running*).
- Python 3.10 ou mais novo (confira com `python --version`).
- Cerca de 3 GB livres em disco: imagem do Neo4j com o GDS, PyTorch e o modelo de embeddings.
- Chave da [Abacus RouteLLM](https://abacus.ai), para as respostas reais: é o LLM que escreve a resposta e a consulta Cypher.
- Chave do [Groq](https://groq.com) só para refazer a extração de entidades, o que não é preciso para rodar o projeto.

### 2. Clonar e instalar as dependências

```powershell
git clone https://github.com/VictorbSilva/trabalho-graphrag-kag.git
cd trabalho-graphrag-kag
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -r requirements-interface.txt
```

Linux/Mac *(não testado à mão; o CI instala o torch de CPU e o `requirements-dev.txt` no Linux)*:

```bash
git clone https://github.com/VictorbSilva/trabalho-graphrag-kag.git
cd trabalho-graphrag-kag
python3 -m venv .venv
source .venv/bin/activate
pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu   # só no Linux
pip install -r requirements-dev.txt -r requirements-interface.txt
```

No Linux, instale o torch de CPU **antes** dos requirements: o torch do PyPI vem com CUDA e baixa vários GB. O `requirements-dev.txt` já inclui o `requirements-api.txt`. Todo terminal novo precisa ativar o ambiente virtual de novo (a linha com `Activate.ps1` ou `source`).

### 3. Configurar o `.env`

```powershell
copy .env.example .env
```

Linux/Mac: `cp .env.example .env`.

Abra o `.env` num editor e preencha:

| Variável | Valor |
|---|---|
| `NEO4J_PASSWORD` | uma senha sua, com pelo menos 8 caracteres |
| `API_FONTE` | `recuperacao` |
| `API_RESPONDER` | `src.recuperacao.responder:responder` |
| `ABACUS_API_KEY` | a sua chave da Abacus |
| `ABACUS_MODELO` | o modelo da Abacus (o grupo usa `claude-opus-5-5-fast`) |

As outras variáveis podem ficar como estão (`GROQ_API_KEY` só é usada para refazer a extração). O `.env` está no `.gitignore` e **nunca vai para o Git**: as chaves ficam só nele, nunca no `.env.example`. A senha do Neo4j é gravada na primeira subida do banco; para trocá-la depois, é preciso apagar o banco (`docker compose down -v`).

### 4. Subir o banco

```powershell
docker compose up -d
```

Na primeira vez demora alguns minutos: o Docker constrói a imagem do Neo4j com APOC e GDS. O serviço `neo4j-schema` espera o banco ficar pronto, aplica constraints e índices e termina sozinho. Para conferir:

- `docker compose logs neo4j-schema` lista os arquivos de schema aplicados.
- No Neo4j Browser, em http://localhost:7474, entre com o usuário `neo4j` e a senha do `.env` e rode `SHOW INDEXES`: aparecem as constraints e os índices do schema, entre eles os fulltext e os vetoriais.

Mais detalhes em [neo4j/README.md](neo4j/README.md#subir-o-banco).

### 5. Carregar os dados

Escolha **uma** das duas fontes:

| Fonte | Comando | Para quê | Contagem no fim (banco vazio antes) |
|---|---|---|---|
| Semente: 4 artigos anotados à mão | `python -m src.recuperacao.carregar_semente` | avaliação, demo e a pergunta de teste do passo 8 | 4 documentos, 12 trechos, 13 entidades, 19 relações |
| Processados: 31 artigos do pipeline | `python -m src.banco.ingestor` | o grafo completo, de `data/processado/extraido` | as que o comando imprimir no fim (o relatório em [docs/relatorio-grafo.md](docs/relatorio-grafo.md) é da carga com 17 artigos) |

Na primeira execução o comando baixa o modelo de embeddings (cerca de 470 MB). No fim, os dois comandos imprimem as contagens do banco (a semente, em JSON: `{"documentos": 4, "trechos": 12, ...}`).

**Não carregue as duas no mesmo banco:** elas usam os mesmos ids de documento e de trecho, com textos diferentes. Para trocar de uma para a outra, apague o banco, suba de novo e carregue a outra (depois, refaça o passo 6):

```powershell
docker compose down -v
docker compose up -d
```

Detalhes do ingestor em [neo4j/README.md](neo4j/README.md#carregar-os-dados-ingestor). O dataset processado já está no repositório, então não é preciso refazer o pipeline Text-to-Graph; se quiser, veja [Refazer o dataset (opcional)](#refazer-o-dataset-opcional).

### 6. Rodar os algoritmos de grafo (GDS)

```powershell
docker compose run --rm neo4j-gds
```

Calcula o PageRank e as comunidades (Louvain) das entidades e grava o resultado no banco. Rode de novo sempre que recarregar os dados.

### 7. Subir a API

```powershell
uvicorn src.api.app:app --port 8000
```

Deixe este terminal aberto. Para conferir, no navegador:

- http://localhost:8000/saude responde `{"status":"ok","fonte":"recuperacao","neo4j":"ok"}`. Se aparecer `"fonte":"exemplo"`, a API não está usando a recuperação real: confira `API_FONTE` no `.env` e reinicie a API. Se aparecer `"neo4j":"fora do ar"` (HTTP 503), o banco não está respondendo: confira o passo 4 e a senha do `.env`.
- http://localhost:8000/docs abre a documentação interativa, onde dá para testar o `POST /perguntar`.

Pela linha de comando, num segundo terminal:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/perguntar -ContentType "application/json; charset=utf-8" -Body '{"pergunta": "Quem criou o C?", "modo": "graphrag"}'
```

Linux/Mac (ou o Git Bash no Windows):

```bash
curl -X POST http://localhost:8000/perguntar -H "Content-Type: application/json" -d '{"pergunta": "Quem criou o C?", "modo": "graphrag"}'
```

O `POST /perguntar` recebe `pergunta` e `modo` (`graphrag` ou `vetorial`) e devolve o objeto do contrato da resposta ([src/contrato.py](src/contrato.py), exemplo em [data/exemplo_resposta.json](data/exemplo_resposta.json)). Com `API_FONTE=exemplo` (o padrão), a API devolve sempre esse JSON de exemplo, sem banco nem LLM. As outras variáveis da API (`API_TIMEOUT_S`, `API_CORS_ORIGENS`) estão no `.env.example`.

### 8. Abrir a interface e fazer a primeira pergunta

Abra um segundo terminal na pasta do projeto, ative o ambiente virtual (`.venv\Scripts\Activate.ps1`; Linux/Mac: `source .venv/bin/activate`) e rode:

```powershell
$env:FONTE_DADOS="api"
$env:API_URL="http://localhost:8000/perguntar"
python -m streamlit run src/interface/app.py
```

Linux/Mac:

```bash
export FONTE_DADOS=api
export API_URL=http://localhost:8000/perguntar
python -m streamlit run src/interface/app.py
```

A interface **não lê o `.env`**: as duas variáveis precisam estar definidas no terminal onde o Streamlit roda, e valem só para aquele terminal. Sem elas, a barra lateral mostra "Fonte de dados: JSON" e a resposta é sempre a do exemplo.

A interface abre em http://localhost:8501. Com a semente carregada, pergunte:

> Que prêmio recebeu quem criou a linguagem que influenciou o C++?

A resposta cita Dennis Ritchie e o Prêmio Turing, com o subgrafo, os caminhos do grafo usados, as fontes e o nível de confiança. A primeira pergunta depois de subir a API demora mais, porque a API carrega o modelo de embeddings (e o baixa, cerca de 470 MB, se o passo 5 ainda não tiver baixado). As seguintes são mais rápidas.

Agente Mentor (opcional, usa a mesma chave da Abacus): `python -m src.mentor.chat`, ver [docs/mentor.md](docs/mentor.md).

### 9. Testes

```powershell
python -m pytest
```

`python -m pytest` roda a suíte inteira (banco, pipeline, recuperação, API e Mentor). Os testes que dependem de serviço externo têm marcador e podem ser rodados à parte:

| Comando | O que roda |
|---|---|
| `python -m pytest -m neo4j` | só os testes que precisam do Neo4j no ar (os que usam a conexão com o banco) |
| `python -m pytest -m llm` | só os testes que precisam de chave de LLM |
| `python -m pytest -m modelo` | só os testes que precisam do modelo de embeddings baixado |
| `python -m pytest -m "not neo4j and not llm and not modelo"` | só os que rodam em qualquer máquina (é o que o CI roda) |

Se o Neo4j estiver fora do ar, os testes do banco aparecem como pulados, com o motivo no resumo. Para exigir o banco, rode com `EXIGIR_NEO4J=1`. Teste novo que chama um LLM deve levar `@pytest.mark.llm`. O CI do GitHub ([.github/workflows/testes.yml](.github/workflows/testes.yml)) roda a cada push na `main` e em todo pull request.

### 10. Avaliação (RAG vetorial vs GraphRAG)

Para conferir os números da avaliação do artigo a partir das respostas salvas, sem banco nem LLM:

```powershell
python -m src.avaliacao.comparar --so-relatorio
```

O comando refaz [docs/avaliacao-resultados.md](docs/avaliacao-resultados.md) a partir de `data/avaliacao/resultados/respostas.json` e da classificação manual (`data/avaliacao/classificacao.json`). Para conferir, rode `git diff docs/avaliacao-resultados.md`: as tabelas com os números não mudam. Mudam só a data e a seção "Análise de erros", que foi escrita à mão e que o comando troca pelo modelo vazio. Para voltar ao arquivo versionado:

```powershell
git restore docs/avaliacao-resultados.md
```

**Cuidado:** sem a flag, `python -m src.avaliacao.comparar` refaz as 15 perguntas nos dois modos e **sobrescreve** `data/avaliacao/resultados/respostas.json`, o relatório e a planilha. Ele precisa do banco com a semente, do GDS e da chave da Abacus, e o resultado depende do que estiver no banco *(não testado)*.

### Refazer o dataset (opcional)

Não é preciso para rodar o projeto. Os scripts rodam na raiz do repositório, com o ambiente virtual ativo, nesta ordem *(não testados; no teste do zero só foi conferido que os comandos existem, com `--help`)*:

| Ordem | Comando | O que faz |
|---|---|---|
| 1 | `python src/pipeline/baixar_artigos.py` | Baixa os artigos de `data/lista_artigos.txt` para `data/bruto/` e atualiza o `manifesto.json`. Antes, troque o `USER_AGENT` no começo do arquivo pelo seu contato (ver [data/README.md](data/README.md)). |
| 2 | `python src/pipeline/chunking.py` | Divide os artigos em trechos, em `data/processado/chunks/`. |
| 3 | `python src/pipeline/extracao.py --todos --max-chunks 0` | Extrai entidades e relações com o Groq e grava `data/processado/extraido/`. Precisa de `GROQ_API_KEY` no `.env`. Sem as flags, processa só os artigos das perguntas de avaliação e 20 trechos por artigo. |
| 4 | `python src/pipeline/conferir_extracao.py` | Só mostra a cobertura: quantas relações esperadas pelas perguntas de avaliação a extração encontrou. |
| 5 | `python src/pipeline/resolucao_entidades.py`, `python src/pipeline/validacao_semantica.py`, `python src/pipeline/integrar_pa4.py`, `python src/pipeline/exportar_pa4.py` | Independentes entre si. Gravam só em `.cache/`, para auditoria e curadoria. |

Avisos:

- O `data/processado/` versionado é a referência do projeto. Refazer a extração gera arquivos diferentes, porque a saída do LLM varia de uma execução para outra, e os passos 2 e 3 gravam por cima dos arquivos de `data/processado/`.
- Hoje o ingestor carrega `data/processado/extraido`, sem a curadoria do passo 5.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| No Windows, `docker compose` falha com um erro de pipe (`open //./pipe/dockerDesktopLinuxEngine` ou parecido) | O Docker Desktop está fechado. Abra-o, espere aparecer *Engine running* e rode o comando de novo. |
| `docker compose` diz `Defina NEO4J_PASSWORD no arquivo .env`, ou os testes param pedindo `NEO4J_PASSWORD` | Falta o `.env` na raiz do projeto. Faça o passo 3. |
| `docker compose up -d` falha com a porta 7474 ou 7687 ocupada (`port is already allocated` ou `ports are not available`) | Outro programa usa a porta. Mude `NEO4J_HTTP_PORT` ou `NEO4J_BOLT_PORT` no `.env`. Se mudar a porta Bolt, mude também a porta em `NEO4J_URI`. |
| No Linux, o `pip install` baixa vários GB (pacotes `nvidia-*`) | É o torch com CUDA. Instale o torch de CPU antes dos requirements (passo 2). |
| A pergunta volta com `Erro HTTP 500: Erro interno ao processar a pergunta`, e o terminal da API mostra `RuntimeError: ABACUS_API_KEY não definida` | Preencha `ABACUS_API_KEY` e `ABACUS_MODELO` no `.env` (passo 3) e reinicie a API. |
| A interface mostra sempre a mesma resposta de exemplo, e a barra lateral diz "Fonte de dados: JSON" | `FONTE_DADOS` não está definida no terminal do Streamlit. Defina `FONTE_DADOS` e `API_URL` nesse terminal e rode o Streamlit de novo (passo 8). |
| As respostas citam trechos que não batem, ou as contagens do banco não são as do passo 5 | A semente e os processados foram carregados no mesmo banco. Apague o banco (`docker compose down -v`, depois `docker compose up -d`), carregue só uma das fontes e refaça o passo 6. |

Problemas específicos do banco (falha no download do GDS, troca do modelo de embeddings, índices antigos) estão em [neo4j/README.md](neo4j/README.md#problemas-comuns).

## Artigo

O artigo técnico (template da SBC) está em [docs/artigo/artigo.pdf](docs/artigo/artigo.pdf), gerado a partir de [docs/artigo/artigo.tex](docs/artigo/artigo.tex). Como gerar o PDF: [docs/artigo/README.md](docs/artigo/README.md).

## Fluxo de trabalho

- Uma branch por tarefa e pull request revisado por pelo menos um colega antes do merge.
- Cada módulo vem com os próprios testes em `tests/<módulo>/`.
- Todo código ou exemplo de terceiros é creditado.

## Créditos

**Dados.** Os textos do dataset são da [Wikipédia em português](https://pt.wikipedia.org), sob a licença [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt-br). Os autores de cada artigo estão no histórico da respectiva página. O título, a URL e a revisão exata de cada artigo estão em `data/bruto/manifesto.json`. Os arquivos derivados (trechos, extração e semente) seguem a mesma licença.

**Software e serviços usados:**

| O que | Para quê |
|---|---|
| [Neo4j](https://neo4j.com) 5.26 Community, com [APOC](https://neo4j.com/labs/apoc/) e [Graph Data Science](https://neo4j.com/docs/graph-data-science/) | Banco de grafos, índices e algoritmos (PageRank, Louvain) |
| [Driver Python do Neo4j](https://github.com/neo4j/neo4j-python-driver) | Acesso ao banco |
| [sentence-transformers](https://www.sbert.net) e o modelo [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), sobre o [PyTorch](https://pytorch.org) | Embeddings de 384 dimensões |
| [Groq](https://groq.com), modelo `openai/gpt-oss-120b` | Extração de entidades e relações |
| [Gemini API](https://ai.google.dev), modelo `gemini-3.5-flash-lite` | Extração de entidades e relações de parte dos artigos |
| [Abacus RouteLLM](https://abacus.ai) | Geração das respostas e das consultas Cypher |
| [FastAPI](https://fastapi.tiangolo.com), [Uvicorn](https://www.uvicorn.org) e [Pydantic](https://docs.pydantic.dev) | API e contrato da resposta |
| [Streamlit](https://streamlit.io) e [streamlit-agraph](https://github.com/ChrisDelClea/streamlit-agraph) (vis-network) | Interface e visualização do subgrafo |
| [pytest](https://pytest.org) | Testes |
| [Docker](https://www.docker.com) | Ambiente do banco |
