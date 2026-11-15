"""Ordenação semântica dos caminhos com o modelo real (src/recuperacao/multi_hop.py).

Carrega data/semente/ com os embeddings do modelo e confere que a pergunta
multi-hop traz, entre os 5 caminhos, o que liga C++ ao Prêmio Turing.
Precisa do Neo4j no ar e do modelo de embeddings baixado (~470 MB).
"""

import pytest

from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.embeddings import gerar_embedding
from src.recuperacao.multi_hop import expandir
from tests.recuperacao.conftest import PREFIXO, limpar_dados_de_teste

pytestmark = pytest.mark.modelo

P = PREFIXO
PERGUNTA = "Que prêmio recebeu quem criou a linguagem que influenciou o C++?"


@pytest.fixture(scope="module")
def semente_no_banco(driver):
    """Semente ingerida uma vez para o módulo, com o embedding de cada trecho."""
    limpar_dados_de_teste(driver)
    carregar_semente_no_banco(driver, prefixo=PREFIXO)
    yield driver
    limpar_dados_de_teste(driver)


def test_pergunta_multi_hop_traz_o_caminho_do_c_mais_mais_ao_premio_turing(semente_no_banco):
    resultados = buscar_chunks(semente_no_banco, gerar_embedding(PERGUNTA), k=100)
    da_semente = [r for r in resultados if r["chunk_id"].startswith(PREFIXO)][:5]
    ids = [r["chunk_id"] for r in da_semente]
    scores = {r["chunk_id"]: r["score"] for r in da_semente}

    caminhos = expandir(semente_no_banco, ids, limite=5, scores=scores, pergunta=PERGUNTA)

    esperado = {P + "tecnologia:c_mais_mais", P + "premio:premio_turing"}
    assert any(esperado <= {n["id"] for n in c["nos"]} for c in caminhos)
