# Roteiro da demo

Issue #33 (PE7). Demo ao vivo da defesa, com cerca de 5 minutos: três perguntas multi-hop, uma em que o RAG vetorial falha e o GraphRAG acerta, e uma pergunta fora do dataset. Os slides e a divisão de falas estão na G7 (#34).

A demo usa o **grafo semente**: 4 artigos (C, C++, Dennis Ritchie e Ken Thompson) **anotados à mão** pelo Nicolas (ver [data/semente/README.md](../../data/semente/README.md)). Na fala, deixe claro que esse grafo é a anotação manual e que o grafo extraído pelo pipeline (31 dos 32 artigos extraídos; o relatório em [docs/relatorio-grafo.md](../relatorio-grafo.md) descreve o grafo carregado com os 31 artigos curados) é o do passo 5 do README, com os números em [docs/relatorio-grafo.md](../relatorio-grafo.md).

## 1. Antes da defesa (30 minutos antes)

Na máquina da defesa, com o projeto já instalado pelo [README](../../README.md#como-rodar) (passos 1 a 3) e a internet funcionando, porque a resposta depende do LLM da Abacus:

| # | O que fazer | Como conferir |
|---|---|---|
| 1 | Abrir o Docker Desktop e esperar *Engine running* | ícone do Docker sem alerta |
| 2 | `docker compose down -v` e `docker compose up -d` (banco limpo) | `docker compose logs neo4j-schema` termina com `OK` |
| 3 | `python -m src.recuperacao.carregar_semente` | imprime 4 documentos, 12 trechos, 13 entidades e 19 relações |
| 4 | `docker compose run --rm neo4j-gds` | termina sem erro |
| 5 | Terminal 1: `uvicorn src.api.app:app --port 8000`, com `API_FONTE=recuperacao` no `.env` | http://localhost:8000/saude mostra `"status":"ok"`, `"fonte":"recuperacao"` e `"neo4j":"ok"` |
| 6 | Terminal 2: `$env:FONTE_DADOS="api"`, `$env:API_URL="http://localhost:8000/perguntar"` e `python -m streamlit run src/interface/app.py` | a barra lateral da interface diz que a fonte é a API |
| 7 | **Aquecer:** fazer a pergunta 1 uma vez | a primeira pergunta carrega o modelo de embeddings e demora; as seguintes são rápidas |
| 8 | Fazer as perguntas 2 a 4 uma vez e comparar com a tabela da seção 2 | a resposta bate com o "resultado esperado" |
| 9 | Deixar abertos: a interface, o Neo4j Browser (http://localhost:7474) e o vídeo do plano B | |

Se algum passo falhar e não houver tempo para consertar, vá direto para a [seção 3](#3-plano-b).

## 2. Roteiro

Todas as perguntas na interface. Os resultados esperados são as respostas reais do sistema com a semente, gravadas em [docs/artigo/exemplo-resposta-real.json](../artigo/exemplo-resposta-real.json) (pergunta 1) e em [data/avaliacao/resultados/respostas.json](../../data/avaliacao/resultados/respostas.json) (perguntas 2 a 4, que são a P08, a P11 e a P13 da avaliação). O texto do LLM pode mudar um pouco de uma execução para outra; o que precisa bater são as entidades, os caminhos e o nível de confiança.

### Pergunta 1: a pergunta do artigo (3 saltos)

> Que prêmio recebeu quem criou a linguagem que influenciou o C++?

Modo `graphrag`.

- **Resultado esperado:** o C++ foi influenciado pelo C, criado por Dennis Ritchie, que recebeu o **Prêmio Turing** (1983, com Ken Thompson). Confiança **média** (0,59).
- **Caminho C1:** C++ `INFLUENCIADA_POR` C, Dennis Ritchie `CRIOU` C, Dennis Ritchie `RECEBEU` Prêmio Turing.
- **O que mostrar:** o subgrafo com os três saltos, a Cypher gerada pelo LLM (parte do C++, `INFLUENCIADA_POR`, `CRIOU`, `RECEBEU`) e as citações `[C1]` e `[F7]` da resposta, que levam ao trecho do artigo da Wikipédia em "Fontes".

### Pergunta 2: o RAG vetorial falha e o GraphRAG acerta (3 saltos)

> Que prêmio recebeu quem criou a linguagem que deu origem ao C?

Primeiro no modo **`vetorial`**, depois a mesma pergunta no modo **`graphrag`**.

- **Vetorial, resultado esperado:** "Não encontrei essa informação no dataset." Confiança **baixa** (0,00), sem caminhos.
- **GraphRAG, resultado esperado:** a linguagem que deu origem ao C é o **B**, criado por **Ken Thompson**, que recebeu o **Prêmio Turing** em 1983. Confiança **média** (0,63).
- **Caminho C1:** C `INFLUENCIADA_POR` B, Ken Thompson `CRIOU` B, Ken Thompson `RECEBEU` Prêmio Turing.
- **O que falar:** a busca vetorial trouxe os 5 trechos mais parecidos com a pergunta, todos dos artigos do C e do C++. O trecho do prêmio está no artigo de Dennis Ritchie e não cita nem o C nem o B, por isso não entrou. O GraphRAG chegou nele seguindo as relações do grafo, porque esse trecho é a fonte da relação `RECEBEU`. É o caso 1 da [análise de erros da avaliação](../avaliacao-resultados.md#análise-de-erros).

### Pergunta 3: agregação sem alucinar (2 saltos)

> Quais pessoas que trabalharam no Bell Labs receberam o Prêmio Turing?

Modo `graphrag`.

- **Resultado esperado:** **Dennis Ritchie e Ken Thompson**. A resposta também diz que Bjarne Stroustrup trabalhou no Bell Labs, mas que o contexto não diz que ele recebeu o prêmio. Confiança **média** (0,65).
- **O que mostrar:** no subgrafo, o Bell Labs ligado às três pessoas e o Prêmio Turing ligado só a duas. O sistema não inventa o prêmio do Stroustrup.

### Pergunta 4: fora do dataset

> Quem criou a linguagem de programação Rust?

Modo `graphrag`.

- **Resultado esperado:** "Não encontrei essa informação no dataset." Confiança **baixa** (0,00).
- **O que falar:** nenhum artigo do dataset trata de Rust. O sistema recusa em vez de responder com o que o LLM sabe de fora, porque a resposta só pode usar o contexto numerado (caminhos C e trechos F).

### Se sobrar tempo

No Neo4j Browser, mostre o grafo e as comunidades:

```cypher
MATCH (e:Entity) RETURN e.name AS entidade, e.pagerank AS pagerank, e.community AS comunidade ORDER BY pagerank DESC LIMIT 10;
```

## 3. Plano B

Do problema mais leve para o mais grave:

| Problema | O que fazer |
|---|---|
| Uma resposta saiu diferente da esperada | Mostre os caminhos e as fontes mesmo assim: o importante é o grafo. Se ficar ruim, mude para o plano B do LLM (linha abaixo). |
| O LLM não responde (sem internet, chave ou cota da Abacus) e a interface mostra erro 500 | **Respostas gravadas.** No `.env`, troque para `API_FONTE=gravado` e reinicie a API (Ctrl+C no terminal 1 e `uvicorn src.api.app:app --port 8000` de novo). As quatro perguntas do roteiro, nos modos acima, devolvem as respostas reais gravadas, com subgrafo, Cypher, fontes e confiança. Não precisa de banco nem de internet. **Diga que são respostas gravadas:** a interface mostra o aviso "Resposta gravada (plano B da demo)". |
| O Neo4j não sobe | O mesmo `API_FONTE=gravado` acima. |
| A API ou a interface não sobem | Passe o **vídeo** da demo (seção 4). |
| O computador da defesa não funciona | Passe o **vídeo** de outro computador ou do celular. |

O modo `gravado` responde só às 15 perguntas de avaliação (nos dois modos) e à pergunta 1 (no modo `graphrag`). Qualquer outra pergunta recebe uma resposta dizendo que ela não está gravada. Nunca apresente uma resposta gravada como se fosse ao vivo.

## 4. Vídeo do plano B

- **Quando gravar:** depois de o roteiro rodar inteiro duas vezes seguidas sem intervenção (seção 5).
- **O que gravar:** a seção 2 inteira, na interface, com o modo `recuperacao` (sistema real), em cerca de 4 minutos. Comece mostrando a barra lateral com a fonte API e o `/saude` com `"fonte":"recuperacao"`, para provar que é o sistema real.
- **Como gravar no Windows:** Win+Alt+R (Xbox Game Bar) grava a janela do navegador; para a tela inteira, use o OBS Studio.
- **Onde guardar:** no Google Drive do grupo, com o link no README da entrega. O vídeo não vai para o Git, porque o arquivo é grande.
- **Vídeo gravado em 16/11:** [https://youtu.be/F4irO4cUqcs](https://youtu.be/F4irO4cUqcs), com o sistema real (modo `recuperacao` e o LLM da Abacus).

## 5. Registro dos testes

Executar o roteiro inteiro (seções 1 e 2) **duas vezes seguidas sem intervenção**, na máquina da defesa, e anotar aqui:

| Data | Máquina | Execução | Pergunta 1 | Pergunta 2 (vetorial / graphrag) | Pergunta 3 | Pergunta 4 | Plano B gravado testado | Observações |
|---|---|---|---|---|---|---|---|---|
| 16/11 | Windows 11, notebook do Pedro | ensaio sem chave da Abacus | caminho C1 certo (C++, C, Dennis Ritchie, Prêmio Turing); texto do LLM não gerado | vetorial: só trechos do C e do C++, sem caminho; graphrag: caminho C, B, Ken Thompson, Prêmio Turing, 8 fontes | não testada | não testada | sim: as 4 perguntas, com as respostas e as confianças da seção 2 | Passos 1 a 6 da seção 1 conferidos. Sem `ABACUS_API_KEY`, a API devolve caminhos, fontes e confiança, e o texto vira "Não foi possível gerar a resposta agora". Falta a execução com a chave. |
| 16/11 | Windows 11, notebook do Pedro | 1 (com a chave da Abacus) | ok: C, Dennis Ritchie, Prêmio Turing; confiança média 0,59 | ok: vetorial "Não encontrei" (baixa 0,00); graphrag B, Ken Thompson, Prêmio Turing (média 0,63) | ok: Dennis Ritchie e Ken Thompson, com a ressalva do Stroustrup; média 0,65 | ok: recusa; baixa 0,00 | sim, em 16/11 | Mesmas entidades, caminhos e confianças da seção 2. Os 7 testes com o LLM (`pytest -m llm`) passaram. |
| 16/11 | Windows 11, notebook do Pedro | 2 (com a chave da Abacus) | ok: C, Dennis Ritchie, Prêmio Turing; confiança média 0,59 | ok: vetorial "Não encontrei" (baixa 0,00); graphrag B, Ken Thompson, Prêmio Turing (média 0,63) | ok: Dennis Ritchie e Ken Thompson, com a ressalva do Stroustrup; média 0,65 | ok: recusa; baixa 0,00 | sim, em 16/11 | Logo depois da execução 1, sem intervenção: resultado igual. |
