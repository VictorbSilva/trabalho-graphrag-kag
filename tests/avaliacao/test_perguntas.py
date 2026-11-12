"""Confere o arquivo de perguntas de avaliação (issue #27, PE3). Não precisa de banco nem de LLM."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO = RAIZ / "data" / "avaliacao" / "perguntas.json"
PASTA_BRUTO = RAIZ / "data" / "bruto"

# Schema do domínio (issue #2 e neo4j/dominio.json): prefixo do id -> rótulo
PREFIXOS = {"pessoa", "organizacao", "tecnologia", "premio"}
RELACOES = {
    "CRIOU": ({"pessoa"}, {"tecnologia", "organizacao"}),
    "TRABALHOU_EM": ({"pessoa"}, {"organizacao"}),
    "DESENVOLVIDA_EM": ({"tecnologia"}, {"organizacao"}),
    "INFLUENCIADA_POR": ({"tecnologia"}, {"tecnologia"}),
    "RECEBEU": ({"pessoa"}, {"premio"}),
}
TIPOS = {"um_salto", "multi_hop", "sem_resposta"}
ID_CANONICO = re.compile(r"^([a-z]+):[a-z0-9]+(?:_[a-z0-9]+)*$")

PERGUNTAS = json.loads(ARQUIVO.read_text(encoding="utf-8"))["perguntas"]
# Ids dos artigos do dataset: o nome do .txt é o id do documento (mesmo id do manifesto).
ARTIGOS = {arquivo.stem for arquivo in PASTA_BRUTO.glob("*.txt")}


def _normalizar(texto: str) -> str:
    return " ".join(texto.split())


def _texto_do_artigo(artigo_id: str) -> str:
    return _normalizar((PASTA_BRUTO / f"{artigo_id}.txt").read_text(encoding="utf-8"))


def _prefixo(entidade_id: str) -> str:
    casamento = ID_CANONICO.match(entidade_id)
    assert casamento, f"id fora da regra canônica: {entidade_id}"
    return casamento.group(1)


def _ids(pergunta):
    return [p["id"] for p in pergunta] if isinstance(pergunta, list) else pergunta["id"]


# --- quantidades -------------------------------------------------------------

def test_quinze_perguntas_com_ids_unicos():
    assert len(PERGUNTAS) == 15
    assert len({p["id"] for p in PERGUNTAS}) == 15


def test_distribuicao_por_tipo():
    tipos = Counter(p["tipo"] for p in PERGUNTAS)
    assert set(tipos) <= TIPOS
    assert tipos["multi_hop"] >= 7
    assert tipos["um_salto"] >= 5
    assert 2 <= tipos["sem_resposta"] <= 3


# --- cada pergunta -----------------------------------------------------------

@pytest.mark.parametrize("pergunta", PERGUNTAS, ids=_ids)
def test_campos_obrigatorios(pergunta):
    obrigatorios = {
        "id", "pergunta", "tipo", "saltos", "resposta_esperada", "entidades_resposta",
        "caminho_esperado", "artigos_origem", "evidencias",
    }
    assert obrigatorios <= pergunta.keys()
    assert pergunta["pergunta"].strip().endswith("?")
    assert pergunta["resposta_esperada"].strip()


@pytest.mark.parametrize("pergunta", PERGUNTAS, ids=_ids)
def test_saltos_coerentes_com_o_tipo(pergunta):
    tipo, saltos, caminho = pergunta["tipo"], pergunta["saltos"], pergunta["caminho_esperado"]
    if tipo == "sem_resposta":
        assert saltos == 0 and not caminho and not pergunta["entidades_resposta"]
    elif tipo == "um_salto":
        assert saltos == 1 and len(caminho) == 1
    else:
        assert saltos >= 2 and len(caminho) >= saltos


@pytest.mark.parametrize("pergunta", PERGUNTAS, ids=_ids)
def test_caminho_usa_so_o_schema_do_dominio(pergunta):
    for tripla in pergunta["caminho_esperado"]:
        assert tripla["tipo"] in RELACOES, tripla
        origens, destinos = RELACOES[tripla["tipo"]]
        assert _prefixo(tripla["origem"]) in origens, f"direção errada: {tripla}"
        assert _prefixo(tripla["destino"]) in destinos, f"direção errada: {tripla}"
    for entidade in pergunta["entidades_resposta"]:
        assert _prefixo(entidade) in PREFIXOS


@pytest.mark.parametrize(
    "pergunta", [p for p in PERGUNTAS if p["tipo"] == "multi_hop"], ids=_ids
)
def test_caminho_multi_hop_e_conexo(pergunta):
    """As triplas do caminho formam um único componente ligado (ignorando a direção)."""
    triplas = pergunta["caminho_esperado"]
    alcancados = {triplas[0]["origem"]}
    mudou = True
    while mudou:
        mudou = False
        for t in triplas:
            if {t["origem"], t["destino"]} & alcancados and not {t["origem"], t["destino"]} <= alcancados:
                alcancados |= {t["origem"], t["destino"]}
                mudou = True
    nos = {n for t in triplas for n in (t["origem"], t["destino"])}
    assert alcancados == nos
    assert set(pergunta["entidades_resposta"]) <= nos


@pytest.mark.parametrize(
    "pergunta", [p for p in PERGUNTAS if p["tipo"] != "sem_resposta"], ids=_ids
)
def test_artigos_e_evidencias_existem_no_dataset(pergunta):
    assert pergunta["artigos_origem"]
    assert set(pergunta["artigos_origem"]) <= ARTIGOS
    assert pergunta["evidencias"]
    for evidencia in pergunta["evidencias"]:
        assert evidencia["artigo"] in pergunta["artigos_origem"]
        assert _normalizar(evidencia["trecho"]) in _texto_do_artigo(evidencia["artigo"]), evidencia


@pytest.mark.parametrize(
    "pergunta", [p for p in PERGUNTAS if p["tipo"] == "sem_resposta"], ids=_ids
)
def test_sem_resposta_nao_aparece_em_nenhum_artigo(pergunta):
    assert pergunta["termos_ausentes"]
    for artigo in ARTIGOS:
        texto = _texto_do_artigo(artigo)
        for termo in pergunta["termos_ausentes"]:
            assert not re.search(rf"\b{re.escape(termo)}\b", texto, re.I), (termo, artigo)
