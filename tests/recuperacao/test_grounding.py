"""Contexto numerado e checagem das citações (src/recuperacao/grounding.py, issue V4).

Sem banco e sem LLM: roda no CI.
"""

from src.recuperacao.grounding import citacoes_invalidas, montar_contexto

SUBGRAFO = {
    "nos": [
        {"id": "tecnologia:c_mais_mais", "nome": "C++", "tipo": "Tecnologia"},
        {"id": "tecnologia:c", "nome": "C", "tipo": "Tecnologia"},
        {"id": "pessoa:dennis_ritchie", "nome": "Dennis Ritchie", "tipo": "Pessoa"},
    ],
    "arestas": [
        {"origem": "tecnologia:c_mais_mais", "destino": "tecnologia:c",
         "tipo": "INFLUENCIADA_POR", "fontes": ["c_mais_mais#0"]},
        {"origem": "pessoa:dennis_ritchie", "destino": "tecnologia:c",
         "tipo": "CRIOU", "fontes": ["c#0"]},
    ],
}

CAMINHOS = [
    {
        "id": "C1",
        "nos": ["tecnologia:c_mais_mais", "tecnologia:c", "pessoa:dennis_ritchie"],
        "relacoes": ["INFLUENCIADA_POR", "CRIOU"],
        "fontes": ["c#0", "c_mais_mais#0"],
    },
]

FONTES = [
    {"id": "F1", "chunk_id": "c#0", "trecho": "C foi criada por Dennis Ritchie.",
     "documento": "C (linguagem de programação)", "url": "https://exemplo/c", "score": 0.9},
    {"id": "F2", "chunk_id": "c_mais_mais#0", "trecho": "C++ foi influenciada por C.",
     "documento": "C++", "url": "https://exemplo/cpp", "score": None},
]


def test_contexto_tem_uma_linha_por_caminho_com_a_direcao_das_relacoes():
    linhas = montar_contexto(CAMINHOS, SUBGRAFO, FONTES).splitlines()
    linhas_de_caminho = [linha for linha in linhas if linha.startswith("[C")]
    assert linhas_de_caminho == [
        "[C1] C++ -[INFLUENCIADA_POR]-> C <-[CRIOU]- Dennis Ritchie",
    ]


def test_contexto_tem_uma_linha_por_fonte_com_documento_e_trecho():
    linhas = montar_contexto(CAMINHOS, SUBGRAFO, FONTES).splitlines()
    linhas_de_fonte = [linha for linha in linhas if linha.startswith("[F")]
    assert linhas_de_fonte == [
        "[F1] (C (linguagem de programação)) C foi criada por Dennis Ritchie.",
        "[F2] (C++) C++ foi influenciada por C.",
    ]


def test_citacao_que_nao_existe_e_apontada():
    texto = "Foi Dennis Ritchie [C1] [F2] [F9]."
    assert citacoes_invalidas(texto, CAMINHOS, FONTES) == ["F9"]


def test_resposta_sem_citacao_nao_tem_citacao_invalida():
    assert citacoes_invalidas("Foi Dennis Ritchie.", CAMINHOS, FONTES) == []
