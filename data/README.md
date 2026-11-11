# Dados

Dataset do projeto: cerca de 30 artigos da Wikipédia em português sobre história da computação (linguagens de programação, pessoas, organizações e prêmios que se citam entre si).

## Origem e licença

Os textos vêm da [Wikipédia em português](https://pt.wikipedia.org) e são licenciados sob [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pt-br). Os autores de cada artigo estão no histórico da respectiva página. O título, a URL, a revisão exata e a data de acesso de cada artigo estão em `bruto/manifesto.json`.

Por causa da licença, os arquivos derivados (chunks e JSON extraídos) mantêm o campo `source` com a URL do artigo de origem, e o trabalho deve creditar a Wikipédia.

## Pastas

| Pasta | Conteúdo | Quem gera |
|---|---|---|
| `lista_artigos.txt` | Títulos dos artigos escolhidos | à mão |
| `bruto/` | Texto puro de cada artigo, sem marcação wiki e sem as seções de referências, e `manifesto.json` | `python src/pipeline/baixar_artigos.py` |
| `processado/` | Um JSON por artigo no formato do contrato C1 (sem embeddings) | pipeline de extração |
| `semente/` | Grafo semente anotado à mão | Nicolas |

## Como refazer o download

```bash
python src/pipeline/baixar_artigos.py
```

O script só usa a biblioteca padrão do Python. Antes de rodar, troque o `USER_AGENT` no começo do arquivo pelo seu contato, como a Wikipédia pede.
