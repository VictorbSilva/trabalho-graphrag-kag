"""Posição do primeiro trecho certo de cada pergunta entre os 12 trechos da semente.

Reproduz a medição citada em docs/artigo/secao-recuperacao.md. PERGUNTAS é o
gabarito usado também pelo teste tests/recuperacao/test_busca_semente.py.

Carrega data/semente/ com um prefixo próprio, faz a mesma busca do teste sem
cortar em 3 e apaga os nós do prefixo no fim. Precisa do Neo4j no ar e do modelo
de embeddings baixado.

Uso, na raiz do repositório:

    python -m src.avaliacao.posicoes_semente
"""

from src.recuperacao.busca_vetorial import buscar_chunks
from src.recuperacao.carregar_semente import carregar_semente_no_banco
from src.recuperacao.conexao import obter_driver
from src.recuperacao.embeddings import gerar_embedding

PREFIXO = "posicoes_semente::"
TRECHOS_DA_SEMENTE = 12

# Pergunta -> trechos da semente que sustentam a resposta, cobrindo os quatro artigos.
# Quando mais de um trecho responde, basta um deles entre os 3 primeiros.
PERGUNTAS = {
    "Quem criou a linguagem C?": {"c#0"},
    "Por que a linguagem se chama C?": {"c#1"},
    "Que linguagem a C substituiu nos microcomputadores?": {"c#2"},
    "Qual era o nome original do C++?": {"c_mais_mais#0"},
    "Quando Dennis Ritchie se aposentou?": {"dennis_ritchie#2"},
    "Qual era a tese de doutorado de Dennis Ritchie?": {"dennis_ritchie#3"},
    "Quem sugeriu o nome Unix?": {"dennis_ritchie#4"},
    "Onde Ken Thompson nasceu?": {"ken_thompson#0"},
    # c#0 diz "criada em 1972"; c#1 situa o período mais criativo em 1972.
    "Em que ano a linguagem C foi criada?": {"c#0", "c#1"},
    # c_mais_mais#1 cita Simula e BCPL; c_mais_mais#0 diz que o C++ nasceu como
    # adicional à C; c#2 sustenta a relação C++ INFLUENCIADA_POR C.
    "Que linguagens inspiraram o C++?": {"c_mais_mais#0", "c_mais_mais#1", "c#2"},
    "Que prêmios Dennis Ritchie recebeu?": {"dennis_ritchie#1"},
    # Os dois trechos citam o Multics.
    "Em que projeto Ken Thompson trabalhou nos Bell Labs?": {"ken_thompson#1", "dennis_ritchie#4"},
}


def _apagar_prefixo(driver) -> None:
    for rotulo in ("Entity", "Chunk", "Document"):
        driver.execute_query(
            f"MATCH (n:{rotulo}) WHERE n.id STARTS WITH $p DETACH DELETE n",
            p=PREFIXO,
        )


def _total_de_trechos_com_embedding(driver) -> int:
    registros, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c) AS total"
    )
    return registros[0]["total"]


def ordem_da_semente(driver, pergunta: str) -> list[str]:
    """Ids (sem o prefixo) dos trechos da semente, do mais para o menos parecido.

    Como no teste, a busca percorre todos os trechos do banco e só os do prefixo
    contam, qualquer que seja o resto do banco.
    """
    k = _total_de_trechos_com_embedding(driver)
    resultados = buscar_chunks(driver, gerar_embedding(pergunta), k=k)
    return [
        r["chunk_id"].removeprefix(PREFIXO)
        for r in resultados
        if r["chunk_id"].startswith(PREFIXO)
    ]


def medir_posicoes(driver) -> list[dict]:
    """Para cada pergunta, a posição (a partir de 1) do primeiro trecho certo."""
    _apagar_prefixo(driver)
    carregar_semente_no_banco(driver, prefixo=PREFIXO)
    try:
        linhas = []
        for pergunta, certos in PERGUNTAS.items():
            ordem = ordem_da_semente(driver, pergunta)
            if len(ordem) != TRECHOS_DA_SEMENTE:
                raise RuntimeError(
                    f"A busca trouxe {len(ordem)} trechos da semente, eram esperados {TRECHOS_DA_SEMENTE}."
                )
            posicao = min(ordem.index(c) for c in certos) + 1
            linhas.append({"pergunta": pergunta, "certos": sorted(certos), "posicao": posicao})
        return linhas
    finally:
        _apagar_prefixo(driver)


def tabela_markdown(linhas: list[dict]) -> str:
    saida = [
        "| Pergunta | Trechos certos | Posição | Entre os 3 primeiros |",
        "|---|---|---|---|",
    ]
    for linha in linhas:
        entre_3 = "sim" if linha["posicao"] <= 3 else "não"
        saida.append(
            f"| {linha['pergunta']} | {', '.join(linha['certos'])} | {linha['posicao']} | {entre_3} |"
        )
    acertos = sum(1 for linha in linhas if linha["posicao"] <= 3)
    saida.append("")
    saida.append(f"Total: {acertos} de {len(linhas)}")
    return "\n".join(saida)


def main() -> None:
    print(tabela_markdown(medir_posicoes(obter_driver())))


if __name__ == "__main__":
    main()
