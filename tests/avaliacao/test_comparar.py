"""Testes do executor da comparação RAG vetorial vs GraphRAG (issue V7).

Sem banco, sem modelo e sem LLM: as respostas são falsas, montadas no formato do
contrato (src/contrato.py), para conferir só como cada resposta é avaliada e resumida.
Rodam no CI.
"""

from src.avaliacao.comparar import avaliar, carregar_perguntas, resumir
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
