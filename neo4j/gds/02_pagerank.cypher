// R20 - PageRank: mede a importância de cada entidade no grafo.
// Grava em e.pagerank. A recuperação (Victor) usa esse valor para
// ranquear entidades quando há mais candidatos do que cabe no contexto do LLM.
CALL gds.pageRank.write('entidades', {
  writeProperty: 'pagerank',
  maxIterations: 20,
  dampingFactor: 0.85
})
YIELD nodePropertiesWritten, ranIterations, didConverge
RETURN nodePropertiesWritten AS nos_atualizados, ranIterations AS iteracoes, didConverge AS convergiu;
