"""Verificação da issue V1 com a semente: a pergunta sobre um fato acha o trecho certo.

Carrega data/semente/ com os embeddings do módulo único (o mesmo usado na
pergunta) e confere que um trecho que sustenta o fato fica entre os 3 primeiros.
Precisa do Neo4j no ar e do modelo de embeddings baixado (~470 MB).
"""

import pytest

from src.avaliacao.posicoes_semente import PERGUNTAS
from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.embeddings import dimensoes_do_indice, gerar_embedding
from tests.recuperacao.conftest import PREFIXO, limpar_dados_de_teste

pytestmark = pytest.mark.modelo

# O gabarito (pergunta -> trechos certos) fica em src/avaliacao/posicoes_semente.py,
# que mede a posição de cada um com: python -m src.avaliacao.posicoes_semente


@pytest.fixture(scope="module")
def semente_no_banco(driver):
    """Semente ingerida uma vez para o módulo, com o embedding de cada trecho."""
    limpar_dados_de_teste(driver)
    carregar_semente_no_banco(driver, prefixo=PREFIXO)
    yield driver
    limpar_dados_de_teste(driver)


def total_de_trechos_com_embedding(driver) -> int:
    registros, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c) AS total"
    )
    return registros[0]["total"]


def tres_primeiros_da_semente(driver, pergunta: str) -> list[str]:
    """Ids (sem o prefixo de teste) dos 3 trechos da semente mais parecidos com a pergunta.

    O banco pode ter outros dados (a semente sem prefixo ou o dataset do pipeline).
    A busca percorre todos os trechos e só os deste teste contam, como num banco
    só com a semente, qualquer que seja o tamanho do banco.
    """
    k = total_de_trechos_com_embedding(driver)
    resultados = buscar_chunks(driver, gerar_embedding(pergunta), k=k)
    ids = [r["chunk_id"] for r in resultados if r["chunk_id"].startswith(PREFIXO)]
    return [i.removeprefix(PREFIXO) for i in ids[:3]]


def test_todos_os_trechos_da_semente_tem_embedding(semente_no_banco):
    registros, _, _ = semente_no_banco.execute_query(
        "MATCH (c:Chunk) WHERE c.id STARTS WITH $p RETURN size(c.embedding) AS dim",
        p=PREFIXO,
    )
    assert [r["dim"] for r in registros] == [dimensoes_do_indice()] * 12


@pytest.mark.parametrize(("pergunta", "trechos_certos"), PERGUNTAS.items())
def test_trecho_certo_entre_os_3_primeiros(semente_no_banco, pergunta, trechos_certos):
    assert trechos_certos & set(tres_primeiros_da_semente(semente_no_banco, pergunta))
