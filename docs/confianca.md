# Nível de confiança da resposta

Issue V5. Código em [`src/recuperacao/confianca.py`](../src/recuperacao/confianca.py), testes em [`tests/recuperacao/test_confianca.py`](../tests/recuperacao/test_confianca.py).

Toda resposta traz o campo `confianca` do contrato (`Confianca` em [`src/contrato.py`](../src/contrato.py)):

```json
{"valor": 0.62, "nivel": "media", "criterio": "score 0.82 (cosseno 0.64), similaridade do caminho 0.60, 5 de 5 caminhos com trecho de origem"}
```

O valor sai só de sinais observáveis da recuperação e de a resposta ter sido gerada ou não. Nenhum LLM avalia a própria resposta. A regra abaixo pode ser ajustada depois; quem mudar a fórmula atualiza este documento e os testes juntos.

## Sinais

| Sinal | O que é |
|---|---|
| `melhor_score` | Maior score entre os trechos da busca vetorial, já na escala de 0 a 1 do Neo4j. `None` quando não há score. |
| `caminhos` | Quantos caminhos a expansão multi-hop encontrou no grafo. |
| `caminhos_com_fonte` | Quantos desses caminhos têm trecho de origem (`source_chunk_ids`) em todas as relações. |
| `similaridade_caminho` | Maior `similaridade` entre os caminhos da expansão: produto escalar entre os vetores normalizados da pergunta e da frase do caminho (o cosseno, de -1 a 1), calculado em [`src/recuperacao/multi_hop.py`](../src/recuperacao/multi_hop.py). `None` sem caminhos ou sem o campo. |
| `resposta_gerada` | `False` quando o LLM levantou erro ou recusou a pergunta; `True` no resto. |
| `cypher_ok` | Resultado do Text-to-Cypher: `True` se rodou, `False` se deu erro, `None` se não foi usado. |
| `sem_contexto` | `True` quando a recuperação não trouxe nada para o LLM usar. |

O responder considera recusa o texto que, em minúsculas, sem pontuação final e sem espaços sobrando, começa com `Não encontrei essa informação no dataset` (a `MENSAGEM_SEM_INFORMACAO` de [`src/recuperacao/grounding.py`](../src/recuperacao/grounding.py), normalizada do mesmo jeito). Assim, pequenas variações do LLM na pontuação ou nos espaços ainda contam como recusa.

Entradas impossíveis (`caminhos` ou `caminhos_com_fonte` negativos, `caminhos_com_fonte` maior que `caminhos`, `melhor_score` fora de 0 a 1, `similaridade_caminho` fora de -1 a 1) são recusadas com `ValueError`, em vez de corrigidas, para que o limite de 0 a 1 não esconda um erro de quem chamou.

## Conversão do score do Neo4j

O índice vetorial do Neo4j usa similaridade por cosseno, mas devolve o score convertido para a faixa de 0 a 1:

```
score = (1 + cosseno) / 2
```

Nessa escala, dois vetores sem relação nenhuma (cosseno 0) dão score 0,5, não 0. Usar o score direto inflaria a confiança de qualquer pergunta. Por isso a regra volta para o cosseno antes de calcular:

```
cosseno = max(0, 2 * score - 1)
```

Cosseno negativo vira 0. Se `melhor_score` for `None`, o cosseno conta como 0.

## Fórmula

1. Se `sem_contexto` ou se `resposta_gerada` é `False`: valor = 0.
2. Senão, se `caminhos > 0` (modo graphrag): valor = (0,5 × cosseno + 0,5 × max(0, `similaridade_caminho`)) × (`caminhos_com_fonte` / `caminhos`). Se `similaridade_caminho` for `None`, conta como 0.
3. Senão (só busca vetorial): valor = 0,7 × cosseno.
4. Se `cypher_ok` é `False`: valor = valor menos 0,1. Com `None` nada muda.
5. O valor é limitado entre 0 e 1 e arredondado para 2 casas.

A razão `caminhos_com_fonte` / `caminhos` deixou de ser somada porque, com a ingestão atual ([`neo4j/consultas/ingestao_modelo.cypher`](../neo4j/consultas/ingestao_modelo.cypher)), toda relação é gravada com `source_chunk_ids`, então ela vale sempre 1 e somava 0,5 a qualquer resposta do modo graphrag. Agora ela multiplica: só tira confiança quando há caminho sem trecho de origem.

A parte do grafo passa a ser a similaridade do melhor caminho com a pergunta. A expansão sempre acha caminhos a partir dos trechos da busca, então ter caminho não diz nada; um caminho parecido com a pergunta diz.

Recusa ou falha do LLM zeram o valor porque, nesses casos, não há resposta a qual atribuir confiança, por melhores que sejam os trechos recuperados.

A resposta só vetorial tem teto de 0,7. Sem caminho no grafo não há como conferir as relações, então ela chega no máximo ao limite inferior da faixa alta, e só com cosseno 1.

## Níveis

| Nível | Faixa do valor |
|---|---|
| `alta` | 0,7 ou mais |
| `media` | de 0,4 até menos de 0,7 |
| `baixa` | menos de 0,4 |

## Critério

O campo `criterio` é uma frase curta com os valores usados no cálculo, para a interface mostrar ao lado do nível. Exemplos:

- `score 0.82 (cosseno 0.64), similaridade do caminho 0.60, 5 de 5 caminhos com trecho de origem`
- `score 0.95 (cosseno 0.90), 0 caminhos no grafo (só busca vetorial)`
- `score 0.82 (cosseno 0.64), similaridade do caminho ausente (conta 0), 5 de 5 caminhos com trecho de origem`
- `score 0.82 (cosseno 0.64), similaridade do caminho 0.60, 5 de 5 caminhos com trecho de origem, Cypher com erro (menos 0.1)`

Quando `sem_contexto` é `True`, a frase começa com `sem contexto recuperado`. Quando `resposta_gerada` é `False`, ela traz `resposta não gerada (recusa ou falha do LLM)` antes do score.

## Exemplos dos testes

| Caso | `melhor_score` | `caminhos` | `caminhos_com_fonte` | `similaridade_caminho` | `resposta_gerada` | `sem_contexto` | `cypher_ok` | Valor | Nível |
|---|---|---|---|---|---|---|---|---|---|
| Grafo e trechos bons | 0,95 | 3 | 3 | 0,90 | sim | não | `None` | 0,90 | alta |
| Caminho parecido com a pergunta | 0,82 | 5 | 5 | 0,60 | sim | não | `None` | 0,62 | media |
| Caminho pouco parecido com a pergunta | 0,82 | 5 | 5 | 0,20 | sim | não | `None` | 0,42 | media |
| Nenhum caminho com trecho de origem | 0,82 | 5 | 0 | 0,60 | sim | não | `None` | 0,00 | baixa |
| Similaridade ausente | 0,82 | 5 | 5 | `None` | sim | não | `None` | 0,32 | baixa |
| Recusa ou falha do LLM | 0,82 | 5 | 5 | 0,60 | não | não | `None` | 0,00 | baixa |
| Sem contexto | 0,95 | 3 | 3 | 0,90 | sim | sim | qualquer | 0,00 | baixa |
| Só vetorial | 0,95 | 0 | 0 | não usada | sim | não | `None` | 0,63 | media |
| Fora do domínio, só vetorial | 0,60 | 0 | 0 | não usada | sim | não | `None` | 0,14 | baixa |
| Cypher com erro | 0,82 | 5 | 5 | 0,60 | sim | não | `False` | 0,52 | media |
| Score e similaridade máximos | 1,00 | 3 | 3 | 1,00 | sim | não | `None` | 1,00 | alta |
