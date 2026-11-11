"""neo4j/dominio.json: estrutura consistente e regra do id canônico (não precisa do banco)."""

import re

from conftest import carregar_dominio, id_canonico


def test_relacoes_apontam_para_rotulos_existentes():
    dominio = carregar_dominio()
    rotulos = {r["nome"] for r in dominio["rotulos"]}
    for relacao in dominio["relacoes"]:
        assert set(relacao["de"]) <= rotulos, relacao["tipo"]
        assert set(relacao["para"]) <= rotulos, relacao["tipo"]


def test_nomes_seguem_a_convencao_do_neo4j():
    dominio = carregar_dominio()
    for rotulo in dominio["rotulos"]:
        assert re.fullmatch(r"[A-Z][A-Za-z]*", rotulo["nome"]), "rótulo em PascalCase, sem acento"
        assert re.fullmatch(r"[a-z]+", rotulo["prefixo_id"])
    for relacao in dominio["relacoes"]:
        assert re.fullmatch(r"[A-Z]+(_[A-Z]+)*", relacao["tipo"]), "relação em MAIUSCULAS_COM_UNDERSCORE"
    prefixos = [r["prefixo_id"] for r in dominio["rotulos"]]
    assert len(prefixos) == len(set(prefixos))


def test_exemplos_do_id_canonico_seguem_a_regra():
    exemplos = carregar_dominio()["id_canonico"]["exemplos"]
    for nome, esperado in exemplos.items():
        prefixo = esperado.split(":")[0]
        assert id_canonico(prefixo, nome) == esperado


def test_dimensao_do_embedding_e_a_decidida_pelo_grupo():
    assert carregar_dominio()["embedding"]["dimensoes"] == 384
