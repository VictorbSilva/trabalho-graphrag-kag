// Libera a memória da projeção (os resultados já foram gravados no banco).
CALL gds.graph.drop('entidades', false) YIELD graphName
RETURN graphName AS projecao_removida;
