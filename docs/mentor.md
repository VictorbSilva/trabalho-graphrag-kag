# Agente Mentor

O Mentor é um agente de apoio ao grupo: um LLM configurado com o System Prompt
oficial da seção 2 do enunciado ("MENTOR TÉCNICO GRAPHRAG/KAG"). Ele orienta sobre
modelagem LPG, índices do Neo4j, pipeline de NER/RE, grounding e arquitetura
híbrida. Ele não escreve o código da solução: o próprio prompt pede que ele explique
conceitos, mostre pseudocódigo, corrija modelagens e sugira estratégias de depuração.

O Mentor é separado da aplicação: não passa pela API nem pela interface Streamlit.

## De onde vem o prompt

O texto está em [src/mentor/system_prompt.txt](../src/mentor/system_prompt.txt),
copiado da seção 2 do enunciado sem alterações. O chat lê o arquivo como está (só
descarta a quebra de linha final) e o manda como mensagem `system` em toda chamada.
Um teste (`tests/mentor/test_mentor.py`) confere que o prompt enviado é idêntico ao
arquivo.

## Onde está configurado

- Código: [src/mentor/chat.py](../src/mentor/chat.py).
- LLM: Abacus RouteLLM, pelo mesmo cliente da recuperação
  ([src/recuperacao/llm.py](../src/recuperacao/llm.py), `gerar_texto`), com o
  modelo definido em `ABACUS_MODELO` no `.env` e temperatura 0.
- Timeout de 60 s por resposta (as respostas do Mentor são mais longas que as da
  recuperação, que usa 30 s).
- O histórico da conversa fica só na memória do processo: cada pergunta vai com o
  prompt oficial e as mensagens anteriores da mesma sessão. Nada é gravado em disco.

## Como usar

Pré-requisito: `ABACUS_API_KEY` e `ABACUS_MODELO` preenchidos no `.env` (cada
integrante usa a própria chave da Abacus) e as dependências de
`requirements-dev.txt` instaladas no ambiente virtual.

Conversa interativa (digite `sair` ou deixe a linha vazia para encerrar):

```bash
python -m src.mentor.chat
```

Uma pergunta só, com a resposta impressa no terminal:

```bash
python -m src.mentor.chat --uma "pergunta"
```

Sem a chave, ou se o LLM falhar, o chat imprime a mensagem de erro e sai com código 1.

Testes:

```bash
python -m pytest tests/mentor -m "not llm"   # sem chave e sem rede
python -m pytest tests/mentor -m llm         # chama a Abacus de verdade
```

## Acesso sem chave

Link do agente sem código: (preencher)

## Exemplo de uso

Execução real em 15/11/2026, com `ABACUS_MODELO=claude-opus-5-5-fast`. A resposta
está como saiu no terminal, sem edição.

Comando:

```bash
python -m src.mentor.chat --uma "No nosso grafo, a procedência de cada relação fica numa propriedade source_chunk_ids da própria relação, em vez de um nó intermediário. Quais as vantagens e os riscos dessa modelagem?"
```

Pergunta:

> No nosso grafo, a procedência de cada relação fica numa propriedade
> source_chunk_ids da própria relação, em vez de um nó intermediário. Quais as
> vantagens e os riscos dessa modelagem?

Resposta:

````markdown
# Procedência como propriedade da relação (`source_chunk_ids`)

Essa modelagem funciona bem para protótipos, mas tende a falhar quando o sistema começa a ter ciclo de vida de documentos, metadados de extração e requisitos de auditoria.

---

## 1. Vantagens

| Vantagem | Por quê |
|---|---|
| **Schema enxuto** | Menos tipos de nós e relações. O modelo fica fácil de explicar e de consultar. |
| **Travessia barata** | Uma consulta `(a)-[r]->(b)` já traz a evidência, sem hops extras. Isso importa em expansões de vizinhança de 2 ou 3 saltos no retrieval. |
| **Retorno direto para o prompt** | `RETURN a, r, b, r.source_chunk_ids` entrega o triplo com as referências para citação. |
| **Deduplicação natural** | Ao fazer `MERGE` da relação, você acumula IDs na lista em vez de criar arestas paralelas. |
| **Menor volume de armazenamento** | Em grafos com milhões de triplos e poucas evidências por triplo, evita milhões de nós intermediários. |

---

## 2. Riscos

### 2.1 Busca reversa sem índice
A pergunta "quais relações vieram do chunk X?" vira:
```
MATCH ()-[r]->() WHERE $cid IN r.source_chunk_ids
```
Os índices de propriedade de relação no Neo4j 5 não servem para busca por pertinência em listas. O resultado é um **scan de todas as relações** daquele tipo, ou de todas, se o tipo não for especificado. Confirme com `PROFILE`: você verá `DirectedRelationshipTypeScan` ou `AllRelationshipsScan` seguido de `Filter`.

Essa busca reversa é exatamente o que você precisa para:
- reprocessar ou remover um documento,
- explicar "o que o sistema aprendeu deste PDF",
- depurar uma extração ruim.

### 2.2 Integridade referencial inexistente
Os IDs na lista são strings soltas, sem chave estrangeira. Se você re-chunkar um documento (mudar tamanho ou overlap) ou apagar chunks, surgem **referências pendentes** (dangling IDs). O LLM então recebe uma "citação" que não resolve para texto nenhum, o que é um problema direto de grounding.

### 2.3 Remoção de documentos vira coleta de lixo manual
Para apagar um documento você precisa:
1. varrer as relações,
2. remover os IDs da lista,
3. apagar a relação se a lista ficou vazia,
4. eventualmente apagar entidades órfãs.

Isso é caro e fácil de errar.

### 2.4 Sem metadados por evidência
A procedência raramente é só "de qual chunk veio". Em produção você vai querer guardar, **para cada evidência**:
- a confiança do extrator,
- a versão do modelo e do prompt de extração (essencial para reprocessar quando o prompt muda),
- o span de caracteres (offset de início e fim) para destacar o trecho na citação,
- o timestamp de ingestão.

Com propriedade na relação, a saída é usar listas paralelas (`source_chunk_ids[i]` ↔ `confidences[i]`). Esse padrão é frágil: qualquer escrita que dessincronize os índices corrompe silenciosamente a procedência.

### 2.5 Relações "hub" com listas enormes
Relações genéricas (`IS_A`, `PART_OF`, `RELATED_TO`) entre entidades populares acumulam centenas ou milhares de IDs. Cada leitura da relação carrega a lista inteira, mesmo quando você só queria traversar. O registro fica inchado e a expansão de vizinhança fica lenta.

### 2.6 Concorrência na ingestão
- Se o append for feito **no cliente** (ler a lista no Python, modificar, escrever de volta), você terá *lost updates* em ingestão paralela.
- Mesmo com append atômico em Cypher, workers paralelos escrevendo nas mesmas entidades hub geram contenção de lock e **deadlocks** (`TransientError`). Você vai precisar de retry e de particionamento de lotes.

### 2.7 O `MERGE` colapsa fatos com contextos diferentes
"Empresa X `CEO` Pessoa Y" extraído de um documento de 2015 e de outro de 2023 vira **uma** relação com dois chunk IDs. Contradições e qualificadores (tempo, condição, negação) somem. O LLM vê o fato como consolidado quando, na verdade, as fontes divergem. Isso é uma fonte clássica de alucinação "com citação".

### 2.8 Filtros por fonte ficam caros
Controle de acesso (ACL por documento), filtro temporal ("só fontes após 2022") e filtro por tipo de documento exigem `UNWIND` mais um join com `Chunk` **para cada relação candidata** durante o retrieval.

---

## 3. Alternativas

### Opção A: Grafo lexical + grafo de domínio (o mínimo recomendado)
Mantenha nós `Chunk` (com o texto, o embedding e o vínculo com o `Document`) e ligue-os às entidades:

```
(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Entity)
(:Entity)-[:REL {source_chunk_ids}]->(:Entity)
```
Assim você ganha deleção por documento e busca reversa ao nível de entidade. Ainda não resolve os metadados por evidência da relação.

### Opção B: Reificação da afirmação (Assertion/Evidence)
```
(:Entity)<-[:SUBJECT]-(:Assertion {predicate, confidence, extractor_version, valid_from?})-[:OBJECT]->(:Entity)
(:Assertion)-[:EXTRACTED_FROM {char_start, char_end}]->(:Chunk)
```
Cada evidência é cidadã de primeira classe: indexável, deletável, auditável, com metadados próprios. Contradições aparecem como asserções distintas. O custo é mais hops e mais nós.

### Opção C: Híbrida (a que eu recomendo para o projeto de vocês)
Mantenha **as duas camadas**:
- A relação direta `(a)-[:REL]->(b)` como **camada de navegação rápida**, com agregados como `evidence_count`, `max_confidence` e `last_seen`. **Sem** a lista de IDs.
- Nós `Assertion`/`Evidence` como **camada de procedência**, consultados só na etapa de grounding, para os poucos triplos que de fato entram no contexto.

Fluxo de retrieval em pseudocódigo:
```
1. busca vetorial em Chunk.embedding / Entity.embedding  -> entidades-semente
2. expansão Cypher de 1-2 hops pelas relações diretas    -> subgrafo candidato
   (filtrar/ranquear por evidence_count, max_confidence)
3. para os top-k triplos: buscar Assertion -> Chunk       -> trechos + spans
4. prompt: triplos + trechos, exigindo que a resposta cite
   (triplo, chunk_id, span) para cada afirmação
```
A travessia continua barata e o grounding fica completo e auditável. A consistência entre as camadas (o agregado da relação contra as asserções) passa a ser um invariante que você testa.

---

## 4. Diagnósticos para rodar no grafo atual

**Distribuição do tamanho das listas.** Verifica se há relações hub inchadas:
```cypher
MATCH ()-[r]->() WHERE r.source_chunk_ids IS NOT NULL
RETURN type(r) AS tipo, size(r.source_chunk_ids) AS n, count(*) AS qtd
ORDER BY n DESC LIMIT 20
```

**Referências pendentes.** Assume uma constraint de unicidade em `Chunk.id`:
```cypher
MATCH ()-[r]->() UNWIND r.source_chunk_ids AS cid
WITH DISTINCT cid
WHERE NOT EXISTS { MATCH (:Chunk {id: cid}) }
RETURN count(cid) AS dangling
```

**Custo da busca reversa.** Rode com `PROFILE` e anote os *db hits*. Esse é o número que vai crescer linearmente com o grafo:
```cypher
PROFILE MATCH ()-[r]->() WHERE $cid IN r.source_chunk_ids RETURN count(r)
```

---

## 5. Critério de decisão

A propriedade na relação é aceitável **se todas** as condições abaixo forem verdadeiras:
- os documentos nunca são removidos nem re-chunkados,
- não há ACL nem filtro por fonte,
- não há metadados por evidência,
- as listas ficam pequenas (por exemplo, p99 < 20).

Se **qualquer uma** for falsa, migre para a Opção C.

**Pergunta para vocês:** o corpus do projeto é estático ou haverá atualização e remoção de documentos? E o extrator já devolve confiança e spans? As respostas definem se vale a pena fazer a migração agora ou se dá para adiar.
````
