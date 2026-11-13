# Perguntas de avaliação

`perguntas.json` tem as 15 perguntas com gabarito usadas na comparação RAG vetorial vs GraphRAG (issue #27, PE3; quem roda é a V7).

| Tipo | Quantidade | Perguntas |
|---|---|---|
| `um_salto` | 5 | P01 a P05 |
| `multi_hop` (2 ou 3 saltos) | 7 | P06 a P12 |
| `sem_resposta` (fora do dataset) | 3 | P13 a P15 |

## Como foram escritas

- A partir dos textos de `data/bruto/`, sem olhar respostas do sistema, para reduzir o viés de quem construiu a recuperação.
- Só usam os quatro rótulos (`Pessoa`, `Organizacao`, `Tecnologia`, `Premio`) e as cinco relações do schema, na direção do schema (`CRIOU`, `TRABALHOU_EM`, `DESENVOLVIDA_EM`, `INFLUENCIADA_POR`, `RECEBEU`).
- Cada fato do gabarito tem em `evidencias` um trecho literal do artigo que o sustenta.
- Os ids das entidades seguem a regra de id canônico (`pessoa:alan_turing`). Onde a resolução de entidades pode escolher outro id (CERN, Xerox PARC, Simula 67), o campo `observacao` avisa quem for corrigir.
- As perguntas sem resposta usam termos que não aparecem em nenhum artigo (Rust, Margaret Hamilton, Kotlin). A resposta certa é dizer que não encontrou a informação.

## Como carregar

```python
import json
perguntas = json.load(open("data/avaliacao/perguntas.json", encoding="utf-8"))["perguntas"]
```

O formato de cada campo está descrito no próprio arquivo, na chave `formato`. Os testes em `tests/avaliacao/` conferem quantidades, schema, direção das relações e se cada evidência existe no artigo citado.
