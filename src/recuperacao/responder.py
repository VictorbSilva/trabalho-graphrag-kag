"""Ponto de entrada da recuperação: responder(pergunta, modo).

Busca vetorial nos trechos (V1) e, no modo graphrag, expansão multi-hop a partir
deles (V3). O texto da resposta sai do LLM a partir de um contexto numerado (C1,
F1...), com as citações conferidas (V4). A confiança vem de sinais observáveis da
recuperação (V5).
"""

from src.contrato import Resposta
from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.confianca import calcular_confianca
from src.recuperacao.conexao import obter_driver
from src.recuperacao.embeddings import gerar_embedding
from src.recuperacao.grounding import (
    INSTRUCOES,
    MENSAGEM_SEM_INFORMACAO,
    citacoes_invalidas,
    montar_contexto,
    resolver_trechos,
)
from src.recuperacao.llm import gerar_texto
from src.recuperacao.multi_hop import expandir, montar_grafo

MODOS = ("graphrag", "vetorial")
MAX_FONTES = 8
AVISO_SEM_CONTEXTO = "Nenhum trecho ou caminho encontrado."
RESPOSTA_FALHA_LLM = "Não foi possível gerar a resposta agora. Veja os trechos em fontes."


def _fontes(driver, resultados: list[dict], caminhos: list[dict]) -> list[dict]:
    """Trechos da busca primeiro; depois os das arestas que a busca não trouxe, sem score."""
    na_busca = {r["chunk_id"] for r in resultados}
    faltantes: list[str] = []
    for caminho in caminhos:
        for chunk_id in caminho["fontes"]:
            if chunk_id not in na_busca and chunk_id not in faltantes:
                faltantes.append(chunk_id)

    extras = []
    if faltantes and len(resultados) < MAX_FONTES:
        resolvidos = {t["chunk_id"]: t for t in resolver_trechos(driver, faltantes)}
        extras = [{**resolvidos[i], "score": None} for i in faltantes if i in resolvidos]

    trechos = (list(resultados) + extras)[:MAX_FONTES]
    return [{"id": f"F{i}", **t} for i, t in enumerate(trechos, 1)]


def responder(pergunta: str, modo: str = "graphrag", *, driver=None, llm=None) -> dict:
    """Responde a pergunta no formato do contrato (src/contrato.py).

    llm recebe as mensagens no formato chat e devolve o texto; o padrão é o
    gerar_texto da Abacus (src/recuperacao/llm.py).
    """
    if modo not in MODOS:
        raise ValueError(f"Modo inválido: {modo!r}. Use 'graphrag' ou 'vetorial'.")
    driver = driver or obter_driver()
    llm = llm or gerar_texto

    resultados = buscar_chunks(driver, gerar_embedding(pergunta), k=5)

    if modo == "graphrag":
        brutos = expandir(
            driver,
            [r["chunk_id"] for r in resultados],
            limite=5,
            scores={r["chunk_id"]: r["score"] for r in resultados},
            pergunta=pergunta,
        )
        caminhos, subgrafo, nos_consultados = montar_grafo(brutos)
    else:
        brutos = []
        caminhos, subgrafo, nos_consultados = [], {"nos": [], "arestas": []}, []

    fontes = _fontes(driver, resultados, caminhos)
    sem_contexto = not fontes and not caminhos
    avisos = []

    if sem_contexto:
        resposta = MENSAGEM_SEM_INFORMACAO
        avisos.append(AVISO_SEM_CONTEXTO)
    else:
        mensagens = [
            {"role": "system", "content": INSTRUCOES},
            {
                "role": "user",
                "content": montar_contexto(caminhos, subgrafo, fontes) + "\n\nPergunta: " + pergunta,
            },
        ]
        try:
            resposta = llm(mensagens)
        except Exception as erro:
            resposta = RESPOSTA_FALHA_LLM
            avisos.append(f"Falha ao chamar o LLM ({type(erro).__name__}).")

    for citado in citacoes_invalidas(resposta, caminhos, fontes):
        avisos.append(f"A resposta cita {citado}, que não está nos caminhos nem nas fontes.")

    confianca = calcular_confianca(
        melhor_score=max((r["score"] for r in resultados), default=None),
        caminhos=len(caminhos),
        caminhos_com_fonte=sum(1 for c in brutos if all(a["fontes"] for a in c["arestas"])),
        cypher_ok=None,
        sem_contexto=sem_contexto,
    )

    dados = {
        "pergunta": pergunta,
        "modo": modo,
        "resposta": resposta,
        "confianca": confianca,
        "cypher": None,
        "caminhos": caminhos,
        "subgrafo": subgrafo,
        "nos_consultados": nos_consultados,
        "fontes": fontes,
        "avisos": avisos,
    }
    return Resposta.model_validate(dados).model_dump()
