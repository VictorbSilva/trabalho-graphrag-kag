# Artigo técnico

| Arquivo | Conteúdo |
|---|---|
| `artigo.tex` | O artigo, no template da SBC (LaTeX) |
| `referencias.bib` | Referências (BibTeX) |
| `artigo.pdf` | PDF gerado a partir do `artigo.tex` (11 páginas) |
| `secao-recuperacao.md`, `resumo-avaliacao.md`, `exemplo-resposta-real.json` | Material de origem das seções de recuperação e avaliação (Victor) |

## Como gerar o PDF (Overleaf)

1. No [Overleaf](https://www.overleaf.com), crie o projeto a partir do modelo oficial da SBC: **New Project → Templates**, busque por **SBC** e abra o modelo de artigos da Sociedade Brasileira de Computação (*SBC Conferences Template*). Ele já traz o `sbc-template.sty` e o `sbc.bst`.
2. Envie para o projeto (**Upload**) os arquivos `artigo.tex` e `referencias.bib` desta pasta.
3. Em **Menu → Main document**, escolha `artigo.tex`.
4. Compile com **pdfLaTeX** (o padrão). O BibTeX roda sozinho.

Sem os arquivos da SBC, o `artigo.tex` também compila em qualquer LaTeX: o preâmbulo detecta a ausência do `sbc-template.sty` e usa margens, fonte e título equivalentes, com as referências no estilo `apalike`.

O `artigo.pdf` desta pasta foi gerado assim, com o [Tectonic](https://tectonic-typesetting.github.io) (`tectonic artigo.tex`), sem avisos de linha estourando a margem. Para a versão com o estilo exato da SBC (título e referências no formato `[Autor Ano]` do `sbc.bst`), gere no Overleaf como descrito acima e substitua o PDF.

## Antes da versão final

- [x] Nome da instituição no `\address` (UNIPÊ)
- [ ] Nomes completos dos autores conferidos (Victor, Nicolas, Patrick e Gabriel já completos; falta confirmar o do Pedro)
- [ ] Revisão das seções de cada um: pipeline (Patrick), recuperação e avaliação (Victor), trabalhos relacionados e interface (Gabriel)
- [ ] Números do grafo atualizados se o dataset completo for carregado (`python -m src.banco.relatorio`)
- [ ] PDF revisado por pelo menos mais um integrante
