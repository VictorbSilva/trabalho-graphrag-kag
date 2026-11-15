# Interface GraphRAG/KAG — Gabriel (G1 e G2)

## Stack escolhida
- Python
- Streamlit
- JSON estático para desenvolvimento sem depender do backend

## Pré-requisitos
- Python 3.10 ou superior
- Ambiente virtual `.venv` ativado

## Instalação
Na raiz do repositório:

```powershell
python -m pip install streamlit
```

## Execução
Na raiz do repositório:

```powershell
python -m streamlit run src/interface/app.py
```

O navegador abrirá a interface. Se não abrir automaticamente, use o endereço
local informado no terminal (normalmente http://localhost:8501).

## Contrato de resposta
O exemplo está em `data/exemplo_resposta.json` e segue os campos C3/C4:
`pergunta`, `modo`, `resposta`, `confianca`, `cypher`, `caminhos`,
`subgrafo`, `nos_consultados`, `fontes` e `avisos`.

## Trocar JSON pela API
A camada de acesso está isolada em `src/interface/servico.py`.
Quando a API do backend estiver disponível:

1. Configure `FONTE_DADOS=api`.
2. Configure `API_URL` com o endereço real do endpoint POST `/perguntar`.
3. Inicie o backend.
4. Execute novamente a interface.

No Windows PowerShell, apenas para a sessão atual:

```powershell
$env:FONTE_DADOS="api"
$env:API_URL="http://localhost:8000/perguntar"
python -m streamlit run src/interface/app.py
```

A API deve aceitar `{"pergunta": "...", "modo": "graphrag"}` e devolver o objeto
completo do contrato C3/C4. Não configure `api` até receber do responsável pelo
backend o endereço e a confirmação de que o endpoint está funcionando.

## Limites desta versão
- A resposta é demonstrativa quando `FONTE_DADOS=json`.
- Não há consulta real ao Neo4j nesta etapa.
- A visualização interativa do subgrafo será adicionada na tarefa G3.
- O prompt oficial do Mentor está versionado em `src/mentor/system_prompt.txt`;
  a conexão com um LLM depende de configuração própria e não é simulada aqui.


## G3 — Visualização interativa

A interface agora mostra o subgrafo do JSON com nós arrastáveis, seleção por clique, cores por tipo, tamanho baseado no PageRank, rótulos de relações e destaque dos caminhos citados.

Instale as dependências atualizadas e execute a aplicação:

```powershell
pip install -r requirements-interface.txt
python -m streamlit run src/interface/app.py
```

A biblioteca usada é **streamlit-agraph** (baseada em vis-network). A seleção de um nó apresenta seus detalhes abaixo do grafo. Se o JSON não tiver `descricao`, a interface informa isso. O destaque do caminho é baseado em nomes dos nós, conforme o contrato demonstrativo; nomes duplicados podem ser ambíguos.

Os dados continuam demonstrativos; não há consulta real ao Neo4j nesta etapa.
