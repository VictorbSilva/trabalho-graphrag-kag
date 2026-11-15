"""Verificação da issue V1 com a semente: a pergunta sobre um fato acha o trecho certo.

Carrega data/semente/ com os embeddings do módulo único (o mesmo usado na
pergunta) e confere que o trecho que sustenta o fato fica entre os 3 primeiros.
Precisa do Neo4j no ar e do modelo de embeddings baixado (~470 MB).
"""

import pytest

from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.embeddings import dimensoes_do_indice, gerar_embedding, gerar_embeddings
# Dependência: estas três funções vêm de tests/neo4j/conftest.py (a mesma ingestão
# dos testes do banco). Se forem renomeadas ou movidas lá, ajuste este import.
from tests.neo4j.conftest import carregar_semente, com_prefixo, ingerir
from tests.recuperacao.conftest import PREFIXO, limpar_dados_de_teste

pytestmark = pytest.mark.modelo

# Pergunta -> trecho da semente que sustenta a resposta, cobrindo os quatro artigos.
PERGUNTAS = {
    "Quem criou a linguagem C?": "c#0",
    "Por que a linguagem se chama C?": "c#1",
    "Que linguagem a C substituiu nos microcomputadores?": "c#2",
    "Qual era o nome original do C++?": "c_mais_mais#0",
    "Quando Dennis Ritchie se aposentou?": "dennis_ritchie#2",
    "Qual era a tese de doutorado de Dennis Ritchie?": "dennis_ritchie#3",
    "Quem sugeriu o nome Unix?": "dennis_ritchie#4",
    "Onde Ken Thompson nasceu?": "ken_thompson#0",
}


@pytest.fixture(scope="module")
def semente_no_banco(driver):
    """Semente ingerida uma vez para o módulo, com o embedding de cada trecho."""
    limpar_dados_de_teste(driver)
    for artigo in carregar_semente().values():
        vetores = gerar_embeddings([c["text"] for c in artigo["chunks"]])
        chunks = [{**c, "embedding": v} for c, v in zip(artigo["chunks"], vetores)]
        ingerir(driver, com_prefixo({**artigo, "chunks": chunks}, PREFIXO))
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
    total = sum(len(a["chunks"]) for a in carregar_semente().values())
    assert [r["dim"] for r in registros] == [dimensoes_do_indice()] * total


@pytest.mark.parametrize(("pergunta", "trecho_certo"), PERGUNTAS.items())
def test_trecho_certo_entre_os_3_primeiros(semente_no_banco, pergunta, trecho_certo):
    assert trecho_certo in tres_primeiros_da_semente(semente_no_banco, pergunta)
