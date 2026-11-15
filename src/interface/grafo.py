"""Renderização do subgrafo da resposta, sem conexão com Neo4j."""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

CORES = {
    "Tecnologia": "#3B82F6",
    "Pessoa": "#10B981",
    "Premio": "#F59E0B",
    "Prêmio": "#F59E0B",
}


def exibir_grafo(subgrafo: dict, caminhos: list) -> None:
    dados_nos = subgrafo.get("nos", [])
    dados_arestas = subgrafo.get("arestas", [])
    if not dados_nos:
        st.info("Nenhum nó disponível para visualizar nesta resposta.")
        return

    # O contrato de exemplo identifica caminhos por nomes de nós, não por IDs.
    # Caso haja nomes repetidos, o destaque poderá ser ambíguo.
    nomes_caminho = {
        str(nome) for caminho in caminhos for nome in caminho.get("nos", [])
    }
    pares_caminho = set()
    for caminho in caminhos:
        sequencia = [str(x) for x in caminho.get("nos", [])]
        pares_caminho.update(frozenset((a, b)) for a, b in zip(sequencia, sequencia[1:]))

    nos = []
    por_id = {}
    for item in dados_nos:
        ident = str(item.get("id", ""))
        if not ident:
            continue
        nome = str(item.get("nome", ident))
        tipo = str(item.get("tipo", "Outro"))
        try:
            rank = max(0.0, float(item.get("pagerank") or 0))
        except (TypeError, ValueError):
            rank = 0.0
        destaque = nome in nomes_caminho
        nos.append(Node(
            id=ident,
            label=nome,
            title=f"{nome} | Tipo: {tipo} | PageRank: {rank:g}",
            color=CORES.get(tipo, "#8B5CF6"),
            size=min(45, 18 + rank * 6),
            borderWidth=4 if destaque else 1,
            borderWidthSelected=5,
        ))
        por_id[ident] = item

    arestas = []
    for item in dados_arestas:
        origem, destino = str(item.get("origem", "")), str(item.get("destino", ""))
        if origem not in por_id or destino not in por_id:
            continue
        nomes = frozenset((str(por_id[origem].get("nome", origem)), str(por_id[destino].get("nome", destino))))
        destaque = nomes in pares_caminho
        relacao = str(item.get("tipo", "RELACAO"))
        arestas.append(Edge(
            source=origem,
            target=destino,
            label=relacao,
            title=relacao,
            color="#F59E0B" if destaque else "#94A3B8",
            width=4 if destaque else 1.5,
        ))

    st.caption("Arraste os nós e clique em um deles para consultar os detalhes. Contornos e conexões em destaque indicam caminhos citados.")
    config = Config(
        width="100%", height=480, directed=True,
        physics=True, hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FDE68A",
        collapsible=False,
    )
    selecionado = agraph(nodes=nos, edges=arestas, config=config)
    if selecionado is not None:
        item = por_id.get(str(selecionado))
        if item:
            st.markdown(f"**Nó selecionado: {item.get('nome', selecionado)}**")
            st.write(f"Tipo: {item.get('tipo', 'Não informado')}")
            st.write(f"Descrição: {item.get('descricao') or 'Não informada no JSON.'}")
            st.write(f"PageRank: {item.get('pagerank', 'Não informado')}")
            st.write(f"ID: `{selecionado}`")

    st.caption("Cores: azul = Tecnologia · verde = Pessoa · amarelo = Prêmio · roxo = outros tipos.")
