"""Carga de data/semente/ no Neo4j com os embeddings do módulo único.

A demo e os testes da recuperação usam esta mesma função. Por baixo ela chama o
ingestor oficial (src/banco/ingestor.py), que valida cada arquivo, gera os
embeddings com src/recuperacao/embeddings.py (o mesmo módulo usado na pergunta)
e grava com neo4j/consultas/ingestao_modelo.cypher, que faz MERGE pelo id:
carregar duas vezes não duplica nada.

Não carregue junto com data/processado/: a semente usa os mesmos ids de
documento e de trecho (ver data/semente/README.md).

Uso: python -m src.recuperacao.carregar_semente
     (equivale a: python -m src.banco.ingestor data/semente)
"""

import json
from pathlib import Path

from src.banco.ingestor import ArquivoInvalido, ingerir_pasta
from src.recuperacao.conexao import obter_driver
from src.recuperacao.embeddings import gerar_embeddings

RAIZ = Path(__file__).resolve().parents[2]
PASTA_SEMENTE = RAIZ / "data" / "semente"


def carregar_semente_no_banco(driver, prefixo: str = "", gerar_vetores=gerar_embeddings) -> dict:
    """Ingere os arquivos de data/semente/ com o embedding de cada trecho.

    Devolve quantos documentos, trechos, entidades e relações de domínio com o
    prefixo existem no banco depois da carga.
    """
    resultado = ingerir_pasta(driver, PASTA_SEMENTE, prefixo=prefixo, gerar_vetores=gerar_vetores)
    if resultado.invalidos:
        arquivo, erros = next(iter(resultado.invalidos.items()))
        raise ArquivoInvalido(arquivo, erros)
    return resultado.contagens


def main() -> None:
    contagens = carregar_semente_no_banco(obter_driver())
    print(json.dumps(contagens))
    print("Para calcular PageRank e comunidades: docker compose run --rm neo4j-gds")


if __name__ == "__main__":
    main()
