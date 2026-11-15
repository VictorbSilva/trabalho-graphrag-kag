"""Testes do executor da comparação RAG vetorial vs GraphRAG (issue V7).

Sem banco, sem modelo e sem LLM: as respostas são falsas, montadas no formato do
contrato (src/contrato.py), para conferir só como cada resposta é avaliada e resumida.
Rodam no CI.
"""

import json

import pytest

from src.avaliacao import comparar
from src.avaliacao.comparar import (
    _tabela_por_pergunta,
    acrescentar_classificacao,
    avaliar,
    avaliar_respostas_salvas,
    carregar_classificacao,
    carregar_perguntas,
    classificar_sem_resposta,
    gerar_planilha,
    resumir,
)
from src.contrato import Resposta
from src.recuperacao.grounding import MENSAGEM_SEM_INFORMACAO

UM_SALTO = {
    "id": "P01",
    "pergunta": "Quem criou a linguagem de programação Python?",
    "tipo": "um_salto",
    "caminho_esperado": [
        {"origem": "pessoa:guido_van_rossum", "tipo": "CRIOU", "destino": "tecnologia:python"}
    ],
    "evidencias": [
        {"artigo": "python", "trecho": "O Python foi concebido no final de 1989 por Guido van Rossum"}
    ],
}

MULTI_HOP = {
    "id": "P06",
    "pergunta": "Que prêmio recebeu o criador da linguagem Lisp?",
    "tipo": "multi_hop",
    "caminho_esperado": [
        {"origem": "pessoa:john_mccarthy", "tipo": "CRIOU", "destino": "tecnologia:lisp"},
        {"origem": "pessoa:john_mccarthy", "tipo": "RECEBEU", "destino": "premio:premio_turing"},
    ],
    "evidencias": [
        {"artigo": "lisp", "trecho": "Lisp é uma família de linguagens de programação concebida por John McCarthy"},
        {"artigo": "john_mccarthy", "trecho": "Recebeu o Prêmio Turing de 1972"},
    ],
}

SEM_RESPOSTA = {
    "id": "P13",
    "pergunta": "Quem criou a linguagem de programação Rust?",
    "tipo": "sem_resposta",
    "caminho_esperado": [],
    "evidencias": [],
    "termos_ausentes": ["Rust"],
}

TRIPLAS_MULTI_HOP = [
    ("pessoa:john_mccarthy", "CRIOU", "tecnologia:lisp"),
    ("pessoa:john_mccarthy", "RECEBEU", "premio:premio_turing"),
]
TRECHOS_MULTI_HOP = [
    "Lisp é uma família de linguagens de programação concebida por John McCarthy em 1958.",
    "McCarthy foi professor em Stanford. Recebeu o Prêmio Turing de 1972.",
]


def _resposta(pergunta, modo="graphrag", texto="Resposta [F1].", trechos=(), arestas=()):
    """Resposta falsa validada pelo contrato, com esses trechos em fontes e essas arestas no subgrafo."""
    fontes = [
        {
            "id": f"F{i}",
            "chunk_id": f"doc#{i}",
            "trecho": trecho,
            "documento": "Documento",
            "url": "https://pt.wikipedia.org/wiki/Documento",
            "score": 0.8,
        }
        for i, trecho in enumerate(trechos, 1)
    ]
    dados = {
        "pergunta": pergunta["pergunta"],
        "modo": modo,
        "resposta": texto,
        "confianca": {"valor": 0.6, "nivel": "media", "criterio": "teste"},
        "subgrafo": {
            "nos": [],
            "arestas": [
                {"origem": origem, "tipo": tipo, "destino": destino, "fontes": ["doc#1"]}
                for origem, tipo, destino in arestas
            ],
        },
        "fontes": fontes,
    }
    return Resposta.model_validate(dados).model_dump()


# --- a) evidência recuperada --------------------------------------------------

def test_evidencia_recuperada_mesmo_com_espacos_diferentes():
    trecho = "Python é uma linguagem.\nO Python  foi concebido no final\n de 1989 por\tGuido van Rossum, no CWI."
    linha = avaliar(UM_SALTO, _resposta(UM_SALTO, trechos=[trecho]))
    assert linha["evidencia_recuperada"] is True


def test_evidencia_nao_recuperada_quando_nenhuma_fonte_tem_o_trecho():
    linha = avaliar(UM_SALTO, _resposta(UM_SALTO, trechos=["Python é uma linguagem de alto nível."]))
    assert linha["evidencia_recuperada"] is False


def test_evidencia_recuperada_exige_todas_as_evidencias_da_pergunta():
    so_uma = avaliar(MULTI_HOP, _resposta(MULTI_HOP, trechos=TRECHOS_MULTI_HOP[:1]))
    todas = avaliar(MULTI_HOP, _resposta(MULTI_HOP, trechos=TRECHOS_MULTI_HOP))
    assert so_uma["evidencia_recuperada"] is False
    assert todas["evidencia_recuperada"] is True


# --- b) caminho completo ------------------------------------------------------

def test_caminho_completo_quando_todas_as_triplas_estao_nas_arestas():
    arestas = TRIPLAS_MULTI_HOP + [("tecnologia:lisp", "INFLUENCIADA_POR", "tecnologia:fortran")]
    linha = avaliar(MULTI_HOP, _resposta(MULTI_HOP, arestas=arestas))
    assert linha["caminho_completo"] is True


def test_caminho_incompleto_quando_falta_uma_tripla():
    linha = avaliar(MULTI_HOP, _resposta(MULTI_HOP, arestas=TRIPLAS_MULTI_HOP[:1]))
    assert linha["caminho_completo"] is False


def test_caminho_incompleto_quando_a_aresta_esta_na_direcao_contraria():
    invertidas = [(destino, tipo, origem) for origem, tipo, destino in TRIPLAS_MULTI_HOP]
    linha = avaliar(MULTI_HOP, _resposta(MULTI_HOP, arestas=invertidas))
    assert linha["caminho_completo"] is False


# --- c) recusa correta --------------------------------------------------------

def test_recusa_correta_quando_sem_resposta_traz_a_mensagem():
    linha = avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, texto=MENSAGEM_SEM_INFORMACAO))
    assert linha["recusa_correta"] is True


def test_recusa_incorreta_quando_sem_resposta_responde_outra_coisa():
    linha = avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, texto="Rust foi criada por Graydon Hoare [F1]."))
    assert linha["recusa_correta"] is False


def test_recusa_nao_se_aplica_aos_outros_tipos():
    resposta = _resposta(UM_SALTO, texto=MENSAGEM_SEM_INFORMACAO)
    assert avaliar(UM_SALTO, resposta)["recusa_correta"] is None
    assert avaliar(MULTI_HOP, _resposta(MULTI_HOP, texto=MENSAGEM_SEM_INFORMACAO))["recusa_correta"] is None


# --- d) carregar_perguntas ----------------------------------------------------

def test_carregar_perguntas_devolve_as_15():
    perguntas = carregar_perguntas()
    assert len(perguntas) == 15
    assert {p["tipo"] for p in perguntas} == {"um_salto", "multi_hop", "sem_resposta"}


# --- e) resumir ---------------------------------------------------------------

def test_resumir_por_modo_e_por_tipo():
    linhas = [
        # um_salto: o vetorial acha o trecho mas não tem subgrafo; o graphrag acha os dois.
        avaliar(UM_SALTO, _resposta(UM_SALTO, "vetorial", trechos=[UM_SALTO["evidencias"][0]["trecho"]])),
        avaliar(UM_SALTO, _resposta(
            UM_SALTO, "graphrag",
            trechos=[UM_SALTO["evidencias"][0]["trecho"]],
            arestas=[("pessoa:guido_van_rossum", "CRIOU", "tecnologia:python")],
        )),
        # multi_hop: o vetorial não acha nada; o graphrag acerta uma das duas vezes.
        avaliar(MULTI_HOP, _resposta(MULTI_HOP, "vetorial")),
        avaliar(MULTI_HOP, _resposta(MULTI_HOP, "graphrag", trechos=TRECHOS_MULTI_HOP, arestas=TRIPLAS_MULTI_HOP)),
        avaliar(MULTI_HOP, _resposta(MULTI_HOP, "graphrag")),
        # sem_resposta: o vetorial recusa; o graphrag inventa.
        avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "vetorial", texto=MENSAGEM_SEM_INFORMACAO)),
        avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "graphrag", texto="Foi Graydon Hoare [F1].")),
    ]

    resumo = resumir(linhas)

    assert resumo["vetorial"]["um_salto"]["evidencia_recuperada"] == 1.0
    assert resumo["vetorial"]["um_salto"]["caminho_completo"] == 0.0
    assert resumo["graphrag"]["um_salto"]["evidencia_recuperada"] == 1.0
    assert resumo["graphrag"]["um_salto"]["caminho_completo"] == 1.0

    assert resumo["vetorial"]["multi_hop"]["evidencia_recuperada"] == 0.0
    assert resumo["vetorial"]["multi_hop"]["caminho_completo"] == 0.0
    assert resumo["graphrag"]["multi_hop"]["evidencia_recuperada"] == 0.5
    assert resumo["graphrag"]["multi_hop"]["caminho_completo"] == 0.5
    assert resumo["graphrag"]["multi_hop"]["perguntas"] == 2

    assert resumo["vetorial"]["sem_resposta"]["recusa_correta"] == 1.0
    assert resumo["graphrag"]["sem_resposta"]["recusa_correta"] == 0.0


# --- f) classificação manual em arquivo ---------------------------------------

def _gravar(tmp_path, conteudo):
    caminho = tmp_path / "classificacao.json"
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return caminho


def test_carregar_classificacao_le_o_arquivo(tmp_path):
    conteudo = {"P01": {"vetorial": "correta", "graphrag": "incompleta"}, "P13": {"graphrag": "alucinada"}}
    assert carregar_classificacao(_gravar(tmp_path, conteudo)) == conteudo


def test_carregar_classificacao_sem_arquivo_devolve_vazio(tmp_path):
    assert carregar_classificacao(tmp_path / "nao_existe.json") == {}


def test_carregar_classificacao_recusa_classe_desconhecida(tmp_path):
    caminho = _gravar(tmp_path, {"P01": {"vetorial": "parcial"}})
    with pytest.raises(ValueError, match="parcial"):
        carregar_classificacao(caminho)


def _linhas_de_um_salto():
    return [
        avaliar(UM_SALTO, _resposta(UM_SALTO, "vetorial")),
        avaliar(UM_SALTO, _resposta(UM_SALTO, "graphrag")),
    ]


def test_tabela_mostra_a_classe_do_arquivo_e_vazio_sem_classe():
    tabela = _tabela_por_pergunta(_linhas_de_um_salto(), {"P01": {"graphrag": "incompleta"}})
    vetorial = next(l for l in tabela if l.startswith("| P01 | um_salto | vetorial |"))
    graphrag = next(l for l in tabela if l.startswith("| P01 | um_salto | graphrag |"))
    assert vetorial.endswith("|  |")
    assert graphrag.endswith("| incompleta |")


def test_tabela_sem_classificacao_deixa_a_coluna_vazia():
    tabela = _tabela_por_pergunta(_linhas_de_um_salto())
    assert all(l.endswith("|  |") for l in tabela if l.startswith("| P01 "))


def test_resumir_conta_as_classes_por_modo_e_tipo_ignorando_as_sem_classe():
    linhas = _linhas_de_um_salto() + [
        avaliar(MULTI_HOP, _resposta(MULTI_HOP, "vetorial")),
        avaliar(MULTI_HOP, _resposta(MULTI_HOP, "graphrag")),
        avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "graphrag", texto=MENSAGEM_SEM_INFORMACAO)),
    ]
    classificacao = {
        "P01": {"vetorial": "correta", "graphrag": "correta"},
        "P06": {"vetorial": "alucinada"},
        "P13": {"graphrag": "correta"},
    }

    resumo = resumir(linhas, classificacao)

    assert resumo["vetorial"]["um_salto"]["classificacao"] == {"correta": 1, "incompleta": 0, "alucinada": 0}
    assert resumo["graphrag"]["um_salto"]["classificacao"] == {"correta": 1, "incompleta": 0, "alucinada": 0}
    assert resumo["vetorial"]["multi_hop"]["classificacao"] == {"correta": 0, "incompleta": 0, "alucinada": 1}
    assert resumo["graphrag"]["multi_hop"]["classificacao"] == {"correta": 0, "incompleta": 0, "alucinada": 0}
    assert resumo["graphrag"]["sem_resposta"]["classificacao"] == {"correta": 1, "incompleta": 0, "alucinada": 0}
    assert resumo["vetorial"]["sem_resposta"]["classificacao"] == {"correta": 0, "incompleta": 0, "alucinada": 0}


def test_resumir_sem_classificacao_conta_zero():
    resumo = resumir(_linhas_de_um_salto())
    assert resumo["vetorial"]["um_salto"]["classificacao"] == {"correta": 0, "incompleta": 0, "alucinada": 0}


def test_classificar_sem_resposta_pela_recusa():
    linhas = _linhas_de_um_salto() + [
        avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "vetorial", texto=MENSAGEM_SEM_INFORMACAO)),
        avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "graphrag", texto="Foi Graydon Hoare [F1].")),
    ]
    assert classificar_sem_resposta(linhas) == {"P13": {"vetorial": "correta", "graphrag": "alucinada"}}


def test_classificar_sem_resposta_ignora_linha_com_erro():
    linha = avaliar(SEM_RESPOSTA, _resposta(SEM_RESPOSTA, "vetorial", texto=MENSAGEM_SEM_INFORMACAO))
    com_erro = {**linha, "modo": "graphrag", "recusa_correta": None, "confianca": None, "erro": "RuntimeError: x"}
    assert classificar_sem_resposta([linha, com_erro]) == {"P13": {"vetorial": "correta"}}


def test_acrescentar_classificacao_nunca_sobrescreve_classe_existente():
    existente = {"P13": {"vetorial": "incompleta"}, "P01": {"graphrag": "correta"}}
    novas = {"P13": {"vetorial": "correta", "graphrag": "alucinada"}, "P14": {"vetorial": "correta"}}

    resultado = acrescentar_classificacao(existente, novas)

    assert resultado == {
        "P01": {"graphrag": "correta"},
        "P13": {"vetorial": "incompleta", "graphrag": "alucinada"},
        "P14": {"vetorial": "correta"},
    }
    assert existente == {"P13": {"vetorial": "incompleta"}, "P01": {"graphrag": "correta"}}


# --- g) planilha para a classificação manual -----------------------------------

UM_SALTO_COM_GABARITO = {**UM_SALTO, "resposta_esperada": "Guido van Rossum."}
SEM_RESPOSTA_COM_GABARITO = {**SEM_RESPOSTA, "resposta_esperada": "O dataset não tem essa informação."}


def test_gerar_planilha_tem_cada_pergunta_e_modo_com_a_linha_para_preencher():
    perguntas = [UM_SALTO_COM_GABARITO, SEM_RESPOSTA_COM_GABARITO]
    textos = {
        ("P01", "vetorial"): "Python foi criado por Guido van Rossum [F1].",
        ("P01", "graphrag"): "Guido van Rossum criou o Python [C1][F1].",
        ("P13", "vetorial"): MENSAGEM_SEM_INFORMACAO,
        ("P13", "graphrag"): "Rust foi criada por Graydon Hoare [F1].",
    }
    linhas, respostas = [], []
    for pergunta in perguntas:
        for modo in ("vetorial", "graphrag"):
            resposta = _resposta(pergunta, modo, texto=textos[(pergunta["id"], modo)])
            linhas.append(avaliar(pergunta, resposta))
            respostas.append({"id": pergunta["id"], "modo": modo, "resposta": resposta, "erro": None})

    planilha = gerar_planilha(linhas, perguntas, respostas)

    for pergunta in perguntas:
        assert pergunta["id"] in planilha
        assert pergunta["tipo"] in planilha
        assert pergunta["pergunta"] in planilha
        assert pergunta["resposta_esperada"] in planilha
    for texto in textos.values():
        assert texto in planilha
    assert planilha.count("Classificação: ____") == 4
    assert planilha.count("Evidência recuperada: não (0/1)") == 2
    assert planilha.count("Caminho completo: não (0/1)") == 2
    assert planilha.count("Evidência recuperada: n/a") == 2


def test_gerar_planilha_mostra_o_erro_quando_nao_houve_resposta():
    linhas, respostas = [], []
    for modo in ("vetorial", "graphrag"):
        linha = {
            "id": "P01", "tipo": "um_salto", "modo": modo,
            "evidencia_recuperada": None, "caminho_completo": None, "recusa_correta": None,
            "confianca": None, "erro": "RuntimeError: banco fora do ar",
        }
        linhas.append(linha)
        respostas.append({"id": "P01", "modo": modo, "resposta": None, "erro": linha["erro"]})

    planilha = gerar_planilha(linhas, [UM_SALTO_COM_GABARITO], respostas)

    assert planilha.count("RuntimeError: banco fora do ar") == 2
    assert planilha.count("Classificação: ____") == 2


# --- h) --so-relatorio: relatório a partir das respostas salvas ---------------

def _respostas_salvas():
    """Respostas no formato de data/avaliacao/resultados/respostas.json, com um erro."""
    return [
        {"id": "P01", "modo": "vetorial", "resposta": _resposta(UM_SALTO, "vetorial", texto="Guido [F1]."), "erro": None},
        {"id": "P01", "modo": "graphrag", "resposta": None, "erro": "RuntimeError: banco fora do ar"},
        {
            "id": "P13", "modo": "vetorial",
            "resposta": _resposta(SEM_RESPOSTA, "vetorial", texto=MENSAGEM_SEM_INFORMACAO), "erro": None,
        },
        {
            "id": "P13", "modo": "graphrag",
            "resposta": _resposta(SEM_RESPOSTA, "graphrag", texto=MENSAGEM_SEM_INFORMACAO), "erro": None,
        },
    ]


def test_avaliar_respostas_salvas_refaz_as_linhas_e_mantem_o_erro():
    perguntas = [UM_SALTO_COM_GABARITO, SEM_RESPOSTA_COM_GABARITO]
    respostas = _respostas_salvas()

    linhas = avaliar_respostas_salvas(perguntas, respostas)

    assert [(l["id"], l["modo"]) for l in linhas] == [(r["id"], r["modo"]) for r in respostas]
    assert linhas[0] == avaliar(UM_SALTO_COM_GABARITO, respostas[0]["resposta"])
    assert linhas[1]["erro"] == "RuntimeError: banco fora do ar"
    assert linhas[1]["evidencia_recuperada"] is None and linhas[1]["confianca"] is None
    assert linhas[2]["recusa_correta"] is True


def test_so_relatorio_regenera_so_o_relatorio_sem_chamar_o_responder(tmp_path, monkeypatch):
    arquivos = {
        "ARQUIVO_PERGUNTAS": tmp_path / "perguntas.json",
        "ARQUIVO_RESPOSTAS": tmp_path / "respostas.json",
        "ARQUIVO_CLASSIFICACAO": tmp_path / "classificacao.json",
        "ARQUIVO_RELATORIO": tmp_path / "avaliacao-resultados.md",
        "ARQUIVO_PLANILHA": tmp_path / "avaliacao-planilha.md",
    }
    for nome, caminho in arquivos.items():
        monkeypatch.setattr(comparar, nome, caminho)
    arquivos["ARQUIVO_PERGUNTAS"].write_text(
        json.dumps({"perguntas": [UM_SALTO_COM_GABARITO, SEM_RESPOSTA_COM_GABARITO]}, ensure_ascii=False),
        encoding="utf-8",
    )
    arquivos["ARQUIVO_RESPOSTAS"].write_text(json.dumps(_respostas_salvas(), ensure_ascii=False), encoding="utf-8")
    arquivos["ARQUIVO_CLASSIFICACAO"].write_text(
        json.dumps({"P01": {"vetorial": "incompleta"}, "P13": {"vetorial": "correta"}}), encoding="utf-8"
    )
    antes = {nome: arquivos[nome].read_bytes() for nome in ("ARQUIVO_RESPOSTAS", "ARQUIVO_CLASSIFICACAO")}

    def responder_proibido(*args, **kwargs):
        raise AssertionError("--so-relatorio não pode chamar o responder()")

    monkeypatch.setattr(comparar, "responder", responder_proibido)

    comparar.main(["--so-relatorio"])

    relatorio = arquivos["ARQUIVO_RELATORIO"].read_text(encoding="utf-8")
    assert "| P01 | um_salto | vetorial |" in relatorio
    assert any(l.startswith("| P01 | um_salto | vetorial |") and l.endswith("| incompleta |") for l in relatorio.splitlines())
    assert any(l.startswith("| P13 | sem_resposta | vetorial |") and l.endswith("| correta |") for l in relatorio.splitlines())
    assert "RuntimeError: banco fora do ar" in relatorio
    assert not arquivos["ARQUIVO_PLANILHA"].exists()
    for nome, conteudo in antes.items():
        assert arquivos[nome].read_bytes() == conteudo
