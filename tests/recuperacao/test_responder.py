"""Testes do responder() sem banco, sem modelo e sem LLM (issues V1, V2, V3, V4 e V5).

A busca vetorial, o embedding, a expansão, o Text-to-Cypher e a resolução dos
trechos são trocados por funções falsas, e o LLM é passado como função falsa, para
conferir só como o responder monta a resposta. Rodam no CI.
"""

import json

import pytest

import src.recuperacao.responder as modulo
from src.api.servico import carregar_responder
from src.contrato import Resposta
from src.recuperacao.grounding import MENSAGEM_SEM_INFORMACAO
from src.recuperacao.responder import responder

PERGUNTA = "Que prêmio recebeu quem criou a linguagem que influenciou o C++?"

RESULTADOS = [
    {
        "chunk_id": "c_mais_mais#0",
        "trecho": "C++ foi criada por Bjarne Stroustrup.",
        "documento": "C++",
        "url": "https://pt.wikipedia.org/wiki/C%2B%2B",
        "score": 0.9,
    },
    {
        "chunk_id": "c#0",
        "trecho": "C foi criada por Dennis Ritchie.",
        "documento": "C (linguagem de programação)",
        "url": "https://pt.wikipedia.org/wiki/C_(linguagem_de_programa%C3%A7%C3%A3o)",
        "score": 0.8,
    },
]

CAMINHO = {
    "chunk_origem": "c_mais_mais#0",
    "nos": [
        {"id": "tecnologia:c_mais_mais", "nome": "C++", "tipo": "Tecnologia",
         "pagerank": 0.0, "comunidade": None},
        {"id": "tecnologia:c", "nome": "C", "tipo": "Tecnologia",
         "pagerank": 0.0, "comunidade": None},
    ],
    "arestas": [
        {"origem": "tecnologia:c_mais_mais", "destino": "tecnologia:c",
         "tipo": "INFLUENCIADA_POR", "fontes": ["c_mais_mais#0"]},
    ],
    "score": 0.9,
}

# Caminho que só o Text-to-Cypher acha, no formato de expandir().
CAMINHO_DA_CYPHER = {
    "chunk_origem": None,
    "nos": [
        {"id": "pessoa:bjarne_stroustrup", "nome": "Bjarne Stroustrup", "tipo": "Pessoa",
         "pagerank": 0.0, "comunidade": None},
        {"id": "tecnologia:c_mais_mais", "nome": "C++", "tipo": "Tecnologia",
         "pagerank": 0.0, "comunidade": None},
    ],
    "arestas": [
        {"origem": "pessoa:bjarne_stroustrup", "destino": "tecnologia:c_mais_mais",
         "tipo": "CRIOU", "fontes": ["c_mais_mais#0"]},
    ],
    "score": 0.0,
}

CYPHER = "MATCH p = (:Pessoa)-[:CRIOU]->(:Tecnologia {id: 'tecnologia:c_mais_mais'}) RETURN p LIMIT 25"

# Trechos que só aparecem nas fontes das arestas, fora do resultado da busca.
TRECHOS_DO_BANCO = {
    f"extra#{i}": {
        "chunk_id": f"extra#{i}",
        "trecho": f"Trecho extra {i}.",
        "documento": "Documento extra",
        "url": f"https://exemplo/extra{i}",
    }
    for i in range(10)
}


@pytest.fixture
def chamadas(monkeypatch):
    """Troca embedding, busca, expansão, Text-to-Cypher e resolução por funções falsas.

    O registro guarda o que a busca, a expansão e o Text-to-Cypher devolvem (os
    testes podem trocar) e se a expansão e o Text-to-Cypher foram chamados.
    """
    registro = {
        "resultados": [dict(r) for r in RESULTADOS],
        "caminhos": [CAMINHO],
        "expandir": False,
        "text_to_cypher": {"cypher": CYPHER, "caminhos": [], "erro": None},
        "gerar_e_executar": False,
    }

    def buscar_falso(driver, embedding, k=5):
        return [dict(r) for r in registro["resultados"]]

    def expandir_falso(driver, chunk_ids, **kwargs):
        registro["expandir"] = True
        return registro["caminhos"]

    def resolver_falso(driver, chunk_ids):
        return [dict(TRECHOS_DO_BANCO[i]) for i in chunk_ids if i in TRECHOS_DO_BANCO]

    def gerar_e_executar_falso(driver, pergunta, llm):
        registro["gerar_e_executar"] = True
        return registro["text_to_cypher"]

    monkeypatch.setattr(modulo, "gerar_embedding", lambda t: [0.0])
    monkeypatch.setattr(modulo, "buscar_chunks", buscar_falso)
    monkeypatch.setattr(modulo, "expandir", expandir_falso)
    monkeypatch.setattr(modulo, "gerar_e_executar", gerar_e_executar_falso)
    monkeypatch.setattr(modulo, "resolver_trechos", resolver_falso)
    return registro


def llm_fixo(texto):
    """LLM falso que sempre devolve o mesmo texto e guarda as mensagens recebidas."""
    def llm(mensagens):
        llm.mensagens = mensagens
        return texto
    llm.mensagens = None
    return llm


def test_graphrag_usa_o_texto_do_llm(chamadas):
    dados = responder(PERGUNTA, "graphrag", driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1][F1]."))
    Resposta.model_validate(dados)
    assert dados["modo"] == "graphrag"
    assert dados["resposta"] == "Foi Dennis Ritchie [C1][F1]."
    assert [c["id"] for c in dados["caminhos"]] == ["C1"]
    assert [f["id"] for f in dados["fontes"]] == ["F1", "F2"]
    assert not any("cita" in aviso for aviso in dados["avisos"])
    assert dados["cypher"] == CYPHER
    assert chamadas["expandir"]
    assert chamadas["gerar_e_executar"]


def test_llm_recebe_instrucoes_contexto_e_pergunta(chamadas):
    llm = llm_fixo("Foi Dennis Ritchie [C1].")
    responder(PERGUNTA, "graphrag", driver=object(), llm=llm)
    sistema, usuario = llm.mensagens
    assert sistema["role"] == "system"
    assert usuario["role"] == "user"
    assert "[C1]" in usuario["content"]
    assert "[F1]" in usuario["content"]
    assert usuario["content"].endswith("Pergunta: " + PERGUNTA)


def test_citacao_inexistente_gera_aviso(chamadas):
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [F9]."))
    Resposta.model_validate(dados)
    assert any("F9" in aviso for aviso in dados["avisos"])


def test_falha_do_llm_ainda_devolve_resposta_valida(chamadas):
    def llm_quebrado(mensagens):
        raise RuntimeError("fora do ar")

    dados = responder(PERGUNTA, driver=object(), llm=llm_quebrado)
    Resposta.model_validate(dados)
    assert any("Falha ao chamar o LLM" in aviso for aviso in dados["avisos"])
    assert [f["id"] for f in dados["fontes"]] == ["F1", "F2"]


def test_sem_contexto_recusa_sem_chamar_o_llm(chamadas):
    chamadas["resultados"] = []
    chamadas["caminhos"] = []

    def llm_proibido(mensagens):
        raise AssertionError("o LLM não deveria ser chamado")

    dados = responder(PERGUNTA, driver=object(), llm=llm_proibido)
    Resposta.model_validate(dados)
    assert dados["resposta"] == MENSAGEM_SEM_INFORMACAO
    assert dados["confianca"]["nivel"] == "baixa"
    assert "Nenhum trecho ou caminho encontrado." in dados["avisos"]


def test_vetorial_nao_expande(chamadas):
    dados = responder(PERGUNTA, "vetorial", driver=object(), llm=llm_fixo("Foi Dennis Ritchie [F2]."))
    Resposta.model_validate(dados)
    assert dados["caminhos"] == []
    assert dados["cypher"] is None
    assert not chamadas["expandir"]
    assert not chamadas["gerar_e_executar"]


def test_confianca_vem_dos_sinais_da_recuperacao(chamadas):
    chamadas["resultados"][0]["score"] = 0.95
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    assert dados["confianca"]["nivel"] != "baixa"
    assert "1 de 1 caminhos" in dados["confianca"]["criterio"]


def test_recusa_do_llm_fica_com_confianca_baixa(chamadas):
    chamadas["resultados"][0]["score"] = 0.95
    recusa = MENSAGEM_SEM_INFORMACAO.rstrip(".")
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo(recusa))
    assert dados["resposta"] == recusa
    assert dados["confianca"]["nivel"] == "baixa"
    assert "resposta não gerada" in dados["confianca"]["criterio"]


def test_falha_do_llm_fica_com_confianca_baixa(chamadas):
    chamadas["resultados"][0]["score"] = 0.95

    def llm_quebrado(mensagens):
        raise RuntimeError("fora do ar")

    dados = responder(PERGUNTA, driver=object(), llm=llm_quebrado)
    assert dados["confianca"]["nivel"] == "baixa"


@pytest.fixture
def sinais_da_confianca(monkeypatch):
    """Troca calcular_confianca por uma falsa que guarda os argumentos recebidos."""
    recebidos = {}

    def calcular_falso(**kwargs):
        recebidos.update(kwargs)
        return {"valor": 0.5, "nivel": "media", "criterio": "falso"}

    monkeypatch.setattr(modulo, "calcular_confianca", calcular_falso)
    return recebidos


def test_confianca_recebe_a_maior_similaridade_dos_caminhos(chamadas, sinais_da_confianca):
    chamadas["caminhos"] = [{**CAMINHO, "similaridade": 0.6}, {**CAMINHO, "similaridade": 0.3}]
    responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1][F1]."))
    assert sinais_da_confianca["similaridade_caminho"] == 0.6
    assert sinais_da_confianca["resposta_gerada"] is True


def test_caminho_sem_similaridade_passa_none(chamadas, sinais_da_confianca):
    responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    assert sinais_da_confianca["similaridade_caminho"] is None


def test_vetorial_passa_similaridade_none(chamadas, sinais_da_confianca):
    responder(PERGUNTA, "vetorial", driver=object(), llm=llm_fixo("Foi Dennis Ritchie [F1]."))
    assert sinais_da_confianca["similaridade_caminho"] is None
    assert sinais_da_confianca["caminhos"] == 0
    assert sinais_da_confianca["cypher_ok"] is None


def test_cypher_executada_passa_cypher_ok_true(chamadas, sinais_da_confianca):
    responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    assert sinais_da_confianca["cypher_ok"] is True


def text_to_cypher_que_levanta(driver, pergunta, llm):
    raise RuntimeError("Text-to-Cypher fora do ar")


@pytest.mark.parametrize("como_falha", ["devolve erro", "levanta exceção"])
def test_falha_do_text_to_cypher_nao_derruba_a_resposta(
    chamadas, sinais_da_confianca, monkeypatch, como_falha
):
    if como_falha == "devolve erro":
        chamadas["text_to_cypher"] = {"cypher": None, "caminhos": [], "erro": "Invalid input 'RETURN'"}
    else:
        monkeypatch.setattr(modulo, "gerar_e_executar", text_to_cypher_que_levanta)

    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    Resposta.model_validate(dados)
    assert dados["cypher"] is None
    assert dados["resposta"] == "Foi Dennis Ritchie [C1]."
    assert [c["id"] for c in dados["caminhos"]] == ["C1"]
    assert any("Text-to-Cypher" in aviso for aviso in dados["avisos"])
    assert sinais_da_confianca["cypher_ok"] is False


def test_caminhos_da_cypher_se_juntam_aos_da_expansao_sem_duplicar(chamadas):
    chamadas["text_to_cypher"] = {
        "cypher": CYPHER,
        "caminhos": [dict(CAMINHO, score=0.0, chunk_origem=None), CAMINHO_DA_CYPHER],
        "erro": None,
    }
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1][C2]."))
    Resposta.model_validate(dados)
    assert [(c["id"], c["relacoes"]) for c in dados["caminhos"]] == [
        ("C1", ["INFLUENCIADA_POR"]),
        ("C2", ["CRIOU"]),
    ]
    assert "pessoa:bjarne_stroustrup" in dados["nos_consultados"]
    assert not any("Text-to-Cypher" in aviso for aviso in dados["avisos"])


def test_confianca_conta_os_caminhos_da_cypher(chamadas, sinais_da_confianca):
    chamadas["text_to_cypher"] = {"cypher": CYPHER, "caminhos": [CAMINHO_DA_CYPHER], "erro": None}
    responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    assert sinais_da_confianca["caminhos"] == 2
    assert sinais_da_confianca["caminhos_com_fonte"] == 2


def test_fontes_das_arestas_fora_da_busca_viram_fontes_sem_score(chamadas):
    aresta = {**CAMINHO["arestas"][0], "fontes": ["c_mais_mais#0", "extra#0"]}
    chamadas["caminhos"] = [{**CAMINHO, "arestas": [aresta]}]
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [F3]."))
    Resposta.model_validate(dados)
    assert [f["id"] for f in dados["fontes"]] == ["F1", "F2", "F3"]
    assert dados["fontes"][2]["chunk_id"] == "extra#0"
    assert dados["fontes"][2]["score"] is None
    assert not any("cita" in aviso for aviso in dados["avisos"])


def test_no_maximo_oito_fontes(chamadas):
    aresta = {**CAMINHO["arestas"][0], "fontes": [f"extra#{i}" for i in range(10)]}
    chamadas["caminhos"] = [{**CAMINHO, "arestas": [aresta]}]
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    assert [f["id"] for f in dados["fontes"]] == [f"F{i}" for i in range(1, 9)]


def test_modo_invalido_e_recusado(chamadas):
    with pytest.raises(ValueError):
        responder(PERGUNTA, "hibrido", driver=object(), llm=llm_fixo("x"))


def test_resposta_vira_json(chamadas):
    dados = responder(PERGUNTA, driver=object(), llm=llm_fixo("Foi Dennis Ritchie [C1]."))
    json.dumps(dados, ensure_ascii=False)


def test_api_carrega_o_responder_pela_configuracao():
    alvo = "src.recuperacao.responder:responder"
    assert carregar_responder("recuperacao", alvo) is responder
