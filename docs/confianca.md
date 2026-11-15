# Nível de confiança da resposta

Issue V5. Código em [`src/recuperacao/confianca.py`](../src/recuperacao/confianca.py), testes em [`tests/recuperacao/test_confianca.py`](../tests/recuperacao/test_confianca.py).

Toda resposta traz o campo `confianca` do contrato (`Confianca` em [`src/contrato.py`](../src/contrato.py)):

```json
{"valor": 0.95, "nivel": "alta", "criterio": "score 0.95 (cosseno 0.90), 3 de 3 caminhos com trecho de origem"}
```

O valor sai só de sinais observáveis da recuperação. Nenhum LLM avalia a própria resposta. A regra abaixo é a proposta inicial e pode ser ajustada depois; quem mudar a fórmula atualiza este documento e os testes juntos.

## Sinais

| Sinal | O que é |
|---|---|
| `melhor_score` | Maior score entre os trechos da busca vetorial, já na escala de 0 a 1 do Neo4j. `None` quando não há score. |
| `caminhos` | Quantos caminhos a expansão multi-hop encontrou no grafo. |
| `caminhos_com_fonte` | Quantos desses caminhos têm pelo menos um trecho de origem (`source_chunk_ids`) que sustenta as relações. |
| `cypher_ok` | Resultado do Text-to-Cypher: `True` se rodou, `False` se deu erro, `None` se não foi usado. |
| `sem_contexto` | `True` quando a recuperação não trouxe nada para o LLM usar. |

Entradas impossíveis (`caminhos` ou `caminhos_com_fonte` negativos, `caminhos_com_fonte` maior que `caminhos`, `melhor_score` fora de 0 a 1) são recusadas com `ValueError`, em vez de corrigidas, para que o limite de 0 a 1 não esconda um erro de quem chamou.

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

1. Se `sem_contexto`: valor = 0.
2. Senão, se `caminhos > 0`: valor = 0,5 × cosseno + 0,5 × (`caminhos_com_fonte` / `caminhos`).
3. Senão (só busca vetorial): valor = 0,7 × cosseno.
4. Se `cypher_ok` é `False`: valor = valor menos 0,1. Com `None` nada muda.
5. O valor é limitado entre 0 e 1 e arredondado para 2 casas.

A resposta só vetorial tem teto de 0,7. Sem caminho no grafo não há como conferir as relações, então ela chega no máximo ao limite inferior da faixa alta, e só com cosseno 1.

## Níveis

| Nível | Faixa do valor |
|---|---|
| `alta` | 0,7 ou mais |
| `media` | de 0,4 até menos de 0,7 |
| `baixa` | menos de 0,4 |

## Critério

O campo `criterio` é uma frase curta com os valores usados no cálculo, para a interface mostrar ao lado do nível. Exemplos:

- `score 0.95 (cosseno 0.90), 3 de 3 caminhos com trecho de origem`
- `score 0.95 (cosseno 0.90), 0 caminhos no grafo (só busca vetorial)`
- `score ausente (cosseno 0.00), 2 de 2 caminhos com trecho de origem`
- `score 0.95 (cosseno 0.90), 3 de 3 caminhos com trecho de origem, Cypher com erro (menos 0.1)`

Quando `sem_contexto` é `True`, a frase começa com `sem contexto recuperado`.

## Exemplos dos testes

| Caso | `melhor_score` | `caminhos` | `caminhos_com_fonte` | `cypher_ok` | `sem_contexto` | Valor | Nível |
|---|---|---|---|---|---|---|---|
| Grafo e trechos bons | 0,95 | 3 | 3 | `None` | não | 0,95 | alta |
| Sem contexto | 0,95 | 3 | 3 | qualquer | sim | 0,00 | baixa |
| Só vetorial | 0,95 | 0 | 0 | `None` | não | 0,63 | media |
| Fora do domínio | 0,60 | 0 | 0 | `None` | não | 0,14 | baixa |
| Cypher com erro | 0,95 | 3 | 3 | `False` | não | 0,85 | alta |
| Score ausente | `None` | 2 | 2 | `None` | não | 0,50 | media |
| Score máximo | 1,00 | 3 | 3 | `None` | não | 1,00 | alta |
| Score mínimo com Cypher com erro | 0,00 | 0 | 0 | `False` | não | 0,00 | baixa |
