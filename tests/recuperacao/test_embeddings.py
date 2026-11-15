"""Testes do módulo de embeddings (issue V1). Precisam do modelo baixado (~470 MB)."""

import math

import pytest

from src.recuperacao.embeddings import dimensoes_do_indice, gerar_embedding, gerar_embeddings

pytestmark = pytest.mark.modelo


def similaridade(a: list[float], b: list[float]) -> float:
    """Cosseno entre dois vetores já normalizados: o produto escalar."""
    return sum(x * y for x, y in zip(a, b))


def test_vetor_tem_a_dimensao_do_indice():
    vetor = gerar_embedding("Dennis Ritchie criou a linguagem C.")
    assert len(vetor) == dimensoes_do_indice()
    assert all(isinstance(x, float) for x in vetor)


def test_vetor_e_normalizado():
    vetor = gerar_embedding("O Unix foi desenvolvido no Bell Labs.")
    tamanho = math.sqrt(sum(x * x for x in vetor))
    assert tamanho == pytest.approx(1.0, abs=1e-5)


def test_frases_parecidas_sao_mais_similares_que_sem_relacao():
    original, parafrase, sem_relacao = gerar_embeddings([
        "Dennis Ritchie criou a linguagem C.",
        "A linguagem C foi criada por Dennis Ritchie.",
        "O Brasil ganhou a Copa do Mundo de 2002.",
    ])
    assert similaridade(original, parafrase) > similaridade(original, sem_relacao)


def test_ingestao_e_pergunta_geram_o_mesmo_vetor():
    texto = "Ken Thompson criou a linguagem B."
    do_lote = gerar_embeddings([texto, "um outro texto qualquer no mesmo lote"])[0]
    da_pergunta = gerar_embedding(texto)
    assert da_pergunta == pytest.approx(do_lote, abs=1e-5)