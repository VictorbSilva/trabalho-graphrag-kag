"""Text-to-Cypher com validação antes de executar (src/recuperacao/text_to_cypher.py, issue V2).

Os testes com o banco usam a semente com prefixo e vetores falsos (a geração da
Cypher não depende do embedding) e um LLM falso, menos o marcado com `llm`, que
manda perguntas reais ao LLM da Abacus.
"""

import json

import pytest

from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.text_to_cypher import (
    EXEMPLOS,
    ORCAMENTO_S,
    TIMEOUT_LLM_S,
    garantir_limit,
    gerar_e_executar,
    montar_prompt,
    resolver_entidades,
    validar_cypher,
)
from tests.recuperacao.conftest import PREFIXO, RAIZ
from tests.recuperacao.test_carregar_semente import vetores_falsos

DOMINIO = json.loads((RAIZ / "neo4j" / "dominio.json").read_text(encoding="utf-8"))
RELACOES_DO_DOMINIO = {r["tipo"] for r in DOMINIO["relacoes"]}

CONSULTA_VALIDA = "MATCH p = (:Pessoa)-[:CRIOU]->(:Tecnologia) RETURN p"
CONSULTA_INVALIDA = "MATCH p = (:Pessoa-[:CRIOU]->(:Tecnologia) RETURN p"
CONSULTA_DE_ESCRITA = f"CREATE (:Entity {{id: '{PREFIXO}intruso'}}) RETURN 1"


@pytest.fixture
def semente(banco):
    carregar_semente_no_banco(banco, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    return banco


def llm_em_sequencia(*respostas, relogio=None, demora=0.0):
    """LLM falso que devolve as respostas na ordem (repete a última).

    Guarda as mensagens e os argumentos nomeados de cada chamada. Com relogio
    (um dict {"agora": segundos}), cada chamada avança o relógio em demora.
    """
    def llm(mensagens, **kwargs):
        llm.chamadas.append(mensagens)
        llm.argumentos.append(kwargs)
        if relogio is not None:
            relogio["agora"] += demora
        return respostas[min(len(llm.chamadas), len(respostas)) - 1]
    llm.chamadas = []
    llm.argumentos = []
    return llm


def texto_das_mensagens(mensagens: list[dict]) -> str:
    return "\n".join(m["content"] for m in mensagens)


# ---------- garantir_limit ----------

def test_garantir_limit_acrescenta_limit_25_quando_nao_ha():
    assert garantir_limit("MATCH (n) RETURN n") == "MATCH (n) RETURN n LIMIT 25"


def test_garantir_limit_tira_o_ponto_e_virgula_final():
    assert garantir_limit("MATCH (n) RETURN n;\n") == "MATCH (n) RETURN n LIMIT 25"


@pytest.mark.parametrize("consulta", ["MATCH (n) RETURN n LIMIT 5", "MATCH (n) RETURN n limit 100"])
def test_garantir_limit_mantem_o_limit_existente(consulta):
    assert garantir_limit(consulta) == consulta


# ---------- montar_prompt ----------

def test_prompt_traz_o_schema_do_dominio_json():
    texto = texto_das_mensagens(montar_prompt("Quem criou o C?", []))
    for rotulo in DOMINIO["rotulos"]:
        assert rotulo["nome"] in texto
        assert rotulo["prefixo_id"] + ":" in texto
    for relacao in DOMINIO["relacoes"]:
        assert f"-[:{relacao['tipo']}]->" in texto
    for relacao_lexica in DOMINIO["grafo_lexico"]["relacoes"]:
        assert relacao_lexica in texto


def test_prompt_traz_os_ids_resolvidos_a_pergunta_e_a_regra_do_return_p():
    entidades = [{"id": "tecnologia:c", "nome": "C", "tipo": "Tecnologia", "score": 1.9}]
    sistema, usuario = montar_prompt("Quem criou o C?", entidades)
    assert sistema["role"] == "system"
    assert usuario["role"] == "user"
    assert "tecnologia:c" in usuario["content"]
    assert "Quem criou o C?" in usuario["content"]
    assert "RETURN p" in sistema["content"]


def test_prompt_traz_tres_exemplos():
    texto = texto_das_mensagens(montar_prompt("Quem criou o C?", []))
    assert len(EXEMPLOS) == 3
    for pergunta, consulta in EXEMPLOS:
        assert pergunta in texto
        assert consulta in texto


def test_prompt_traz_o_erro_anterior():
    usuario = montar_prompt("Quem criou o C?", [], erro="Invalid input 'RETURN'", consulta_anterior="MATCH (n")[-1]
    assert "Invalid input 'RETURN'" in usuario["content"]
    assert "MATCH (n" in usuario["content"]


def test_prompt_sem_erro_nao_fala_de_consulta_anterior():
    assert "anterior" not in texto_das_mensagens(montar_prompt("Quem criou o C?", []))


# ---------- com o banco ----------

def test_resolver_entidades_acha_o_id_do_cpp(semente):
    ids = [e["id"] for e in resolver_entidades(semente, "Quem criou o C++?")]
    assert PREFIXO + "tecnologia:c_mais_mais" in ids


def test_validar_cypher_aceita_consulta_valida(semente):
    assert validar_cypher(semente, CONSULTA_VALIDA) is None


def test_validar_cypher_devolve_o_erro_de_sintaxe(semente):
    erro = validar_cypher(semente, CONSULTA_INVALIDA)
    assert isinstance(erro, str) and erro


@pytest.mark.parametrize(("pergunta", "consulta"), EXEMPLOS)
def test_exemplos_do_prompt_sao_validos(semente, pergunta, consulta):
    assert validar_cypher(semente, consulta) is None


def test_escrita_e_recusada_e_nada_e_gravado(semente):
    llm = llm_em_sequencia(CONSULTA_DE_ESCRITA)
    resultado = gerar_e_executar(semente, "Crie um nó", llm=llm)
    assert resultado["cypher"] is None
    assert resultado["caminhos"] == []
    assert resultado["erro"]
    registros, _, _ = semente.execute_query(
        "MATCH (n) WHERE n.id = $id RETURN count(n) AS total", id=PREFIXO + "intruso"
    )
    assert registros[0]["total"] == 0


def test_consulta_invalida_ganha_uma_nova_tentativa_com_o_erro(semente):
    llm = llm_em_sequencia(CONSULTA_INVALIDA, CONSULTA_VALIDA)
    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm)

    assert len(llm.chamadas) == 2
    erro = validar_cypher(semente, garantir_limit(CONSULTA_INVALIDA))
    assert erro in texto_das_mensagens(llm.chamadas[1])
    assert erro not in texto_das_mensagens(llm.chamadas[0])

    assert resultado["erro"] is None
    assert resultado["cypher"] == garantir_limit(CONSULTA_VALIDA)
    assert resultado["caminhos"]


def test_llm_que_sempre_erra_para_na_segunda_chamada(semente):
    llm = llm_em_sequencia(CONSULTA_INVALIDA)
    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm)
    assert len(llm.chamadas) == 2
    assert resultado == {"cypher": None, "caminhos": [], "erro": resultado["erro"]}
    assert resultado["erro"]


def test_falha_do_llm_volta_como_erro(semente):
    def llm_quebrado(mensagens, **kwargs):
        raise RuntimeError("fora do ar")

    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm_quebrado)
    assert resultado["cypher"] is None
    assert resultado["caminhos"] == []
    assert "RuntimeError" in resultado["erro"]


def test_bloco_de_codigo_do_llm_e_removido(semente):
    llm = llm_em_sequencia(f"```cypher\n{CONSULTA_VALIDA}\n```")
    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm)
    assert resultado["cypher"] == garantir_limit(CONSULTA_VALIDA)


def test_caminhos_saem_no_formato_de_expandir(semente):
    consulta = (
        f"MATCH p = (:Pessoa)-[:CRIOU]->(:Tecnologia {{id: '{PREFIXO}tecnologia:c_mais_mais'}}) RETURN p"
    )
    resultado = gerar_e_executar(semente, "Quem criou o C++?", llm=llm_em_sequencia(consulta))
    assert resultado["erro"] is None
    [caminho] = resultado["caminhos"]
    assert set(caminho) == {"chunk_origem", "nos", "arestas", "score"}
    assert [n["id"] for n in caminho["nos"]] == [
        PREFIXO + "pessoa:bjarne_stroustrup",
        PREFIXO + "tecnologia:c_mais_mais",
    ]
    assert set(caminho["nos"][0]) == {"id", "nome", "tipo", "pagerank", "comunidade"}
    [aresta] = caminho["arestas"]
    assert aresta["origem"] == PREFIXO + "pessoa:bjarne_stroustrup"
    assert aresta["destino"] == PREFIXO + "tecnologia:c_mais_mais"
    assert aresta["tipo"] == "CRIOU"
    assert aresta["fontes"] == [PREFIXO + "c_mais_mais#0"]


def test_caminhos_fora_do_dominio_sao_descartados(semente):
    consulta = (
        f"MATCH p = (:Chunk {{id: '{PREFIXO}c_mais_mais#0'}})-[:MENTIONS]->(:Entity) RETURN p"
    )
    resultado = gerar_e_executar(semente, "O que o trecho cita?", llm=llm_em_sequencia(consulta))
    assert resultado["erro"] is None
    assert resultado["caminhos"] == []


# ---------- limites de tempo ----------

def test_cada_chamada_do_llm_usa_timeout_de_10_s(semente):
    llm = llm_em_sequencia(CONSULTA_INVALIDA, CONSULTA_VALIDA)
    gerar_e_executar(semente, "Quem criou o C?", llm=llm)
    assert TIMEOUT_LLM_S == 10
    assert llm.argumentos == [{"timeout": 10}, {"timeout": 10}]


def test_primeira_tentativa_que_estoura_o_orcamento_nao_tem_segunda(semente):
    relogio = {"agora": 0.0}
    llm = llm_em_sequencia(CONSULTA_INVALIDA, relogio=relogio, demora=ORCAMENTO_S + 5)
    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm, relogio=lambda: relogio["agora"])
    assert len(llm.chamadas) == 1
    assert resultado["cypher"] is None
    assert resultado["caminhos"] == []
    assert "orçamento" in resultado["erro"]
    assert f"{ORCAMENTO_S} s" in resultado["erro"]


def test_primeira_tentativa_dentro_do_orcamento_ganha_a_segunda(semente):
    relogio = {"agora": 0.0}
    llm = llm_em_sequencia(CONSULTA_INVALIDA, CONSULTA_VALIDA, relogio=relogio, demora=ORCAMENTO_S - 5)
    resultado = gerar_e_executar(semente, "Quem criou o C?", llm=llm, relogio=lambda: relogio["agora"])
    assert len(llm.chamadas) == 2
    assert resultado["erro"] is None


def test_consulta_que_passa_do_timeout_de_execucao_e_recusada(semente):
    llm = llm_em_sequencia("CALL apoc.util.sleep(6000) RETURN 1")
    resultado = gerar_e_executar(semente, "Espere", llm=llm)
    assert resultado["cypher"] is None
    assert resultado["caminhos"] == []
    assert resultado["erro"]


# ---------- com o LLM de verdade ----------

PERGUNTAS_REAIS = [
    "Quem criou o C++?",
    "Que prêmios Dennis Ritchie recebeu?",
    "Onde Ken Thompson trabalhou?",
    "Quais linguagens influenciaram o C, direta ou indiretamente?",
    "Algum criador de uma linguagem que influenciou o C++ recebeu o Prêmio Turing?",
]


@pytest.mark.llm
@pytest.mark.parametrize("pergunta", PERGUNTAS_REAIS)
def test_cypher_gerada_pelo_llm_executa_sem_erro(semente, pergunta):
    resultado = gerar_e_executar(semente, pergunta)
    assert resultado["erro"] is None, resultado["erro"]
    assert resultado["cypher"]
    for caminho in resultado["caminhos"]:
        assert {a["tipo"] for a in caminho["arestas"]} <= RELACOES_DO_DOMINIO
