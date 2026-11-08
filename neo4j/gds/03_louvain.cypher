// R20 - Louvain: agrupa entidades em comunidades (temas).
// Grava em e.community. Serve para enriquecer o contexto com entidades
// do mesmo tema e para colorir o subgrafo na interface.
// (Leiden seria a alternativa: gds.leiden.write, com os mesmos parâmetros.)
CALL gds.louvain.write('entidades', {
  writeProperty: 'community'
})
YIELD communityCount, modularity, nodePropertiesWritten
RETURN communityCount AS comunidades, modularity AS modularidade, nodePropertiesWritten AS nos_atualizados;
