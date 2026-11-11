"""Interface inicial do projeto GraphRAG/KAG - entregas G1 e G2."""

import streamlit as st

from src.interface.config import FONTE_DADOS
from src.interface.servico import responder
from src.interface.grafo import exibir_grafo

st.set_page_config(
    page_title="GraphRAG & KAG",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 GraphRAG & KAG")
st.caption("Sistema de perguntas e respostas fundamentado em um grafo de conhecimento.")

with st.sidebar:
    st.header("Configurações")
    modo = st.selectbox(
        "Modo de pesquisa",
        options=["graphrag", "vetorial"],
        format_func=lambda valor: "GraphRAG" if valor == "graphrag" else "Busca vetorial"
    )
    st.divider()
    st.caption(f"Fonte de dados configurada: **{FONTE_DADOS.upper()}**")
    st.caption(
        "JSON: demonstração local. API: integração com o backend quando estiver disponível."
    )

st.subheader("Faça sua pergunta")
with st.form("form_pergunta"):
    pergunta = st.text_input(
        "Pergunta",
        placeholder="Ex.: Que prêmio recebeu quem criou a linguagem que influenciou o C++?"
    )
    enviar = st.form_submit_button("Enviar pergunta", type="primary")

if enviar:
    if not pergunta.strip():
        st.warning("Digite uma pergunta antes de enviar.")
    else:
        try:
            with st.spinner("Consultando o sistema..."):
                st.session_state["resultado_consulta"] = responder(pergunta.strip(), modo)
        except (FileNotFoundError, ValueError, RuntimeError) as erro:
            st.error(f"Não foi possível concluir a consulta: {erro}")
        except Exception as erro:
            st.error(f"Ocorreu um erro inesperado: {erro}")

if "resultado_consulta" in st.session_state:
    resultado = st.session_state["resultado_consulta"]
    st.success("Consulta concluída.")
    st.subheader("Resposta")
    st.write(resultado["resposta"])

    confianca = resultado.get("confianca", {})
    valor = confianca.get("valor")
    nivel = confianca.get("nivel", "não informado")
    criterio = confianca.get("criterio", "Critério não informado.")

    col1, col2 = st.columns(2)
    with col1:
        if isinstance(valor, (int, float)):
            st.metric("Confiança demonstrativa", f"{valor:.0%}")
        else:
            st.metric("Nível de confiança", str(nivel).capitalize())
    with col2:
        st.metric("Modo utilizado", str(resultado.get("modo", "")).upper())
    st.caption(f"Critério de confiança: {criterio}")

    st.subheader("Subgrafo interativo")
    exibir_grafo(resultado.get("subgrafo", {}), resultado.get("caminhos", []))

    with st.expander("Ver caminhos e referências"):
        for caminho in resultado.get("caminhos", []):
            st.markdown(f"**Caminho {caminho.get('id', '')}**")
            st.write(" → ".join(str(x) for x in caminho.get("nos", [])))
            st.write("Relações:", ", ".join(str(x) for x in caminho.get("relacoes", [])))
        for fonte in resultado.get("fontes", []):
            st.markdown(f"**[{fonte.get('id', 'Fonte')}] {fonte.get('documento', 'Documento')}**")
            st.write(fonte.get("trecho", "Trecho não informado."))
            url = fonte.get("url")
            if url:
                st.markdown(f"[Abrir fonte]({url})")
            if fonte.get("score") is not None:
                st.caption(f"Score: {fonte['score']}")

    with st.expander("Ver detalhes técnicos"):
        st.markdown("**Nós consultados**")
        st.write(resultado.get("nos_consultados", []))
        st.markdown("**Consulta Cypher**")
        cypher = resultado.get("cypher")
        if cypher:
            st.code(cypher, language="cypher")
        else:
            st.info("A consulta Cypher não foi fornecida.")
        subgrafo = resultado.get("subgrafo", {})
        st.write(f"Nós: {len(subgrafo.get('nos', []))} | Arestas: {len(subgrafo.get('arestas', []))}")
        st.json(subgrafo)

    for aviso in resultado.get("avisos", []):
        st.warning(str(aviso))
    if FONTE_DADOS == "json":
        st.info("Demonstração com JSON estático. A resposta não foi consultada no Neo4j nem gerada pelo backend real.")

st.divider()
st.caption("Interface GraphRAG/KAG — G2 e G3. Visualização: streamlit-agraph (vis-network).")
