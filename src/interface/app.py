"""Interface GraphRAG/KAG — G2, G3 e G4."""
import streamlit as st
from src.interface.config import FONTE_DADOS
from src.interface.servico import responder
from src.interface.grafo import exibir_grafo
from src.interface.paineis import exibir_paineis

st.set_page_config(page_title="GraphRAG & KAG", page_icon="🧠", layout="wide")
st.title("🧠 GraphRAG & KAG")
st.caption("Perguntas e respostas fundamentadas em grafo de conhecimento.")

with st.sidebar:
    st.header("Configurações")
    modo = st.selectbox("Modo de pesquisa", ["graphrag", "vetorial"],
                        format_func=lambda v: "GraphRAG" if v == "graphrag" else "Busca vetorial")
    st.divider()
    st.caption(f"Fonte de dados: **{FONTE_DADOS.upper()}**")
    st.caption("JSON = demonstração local; API = backend real, quando disponível.")

st.subheader("Faça sua pergunta")
with st.form("form_pergunta"):
    pergunta = st.text_input("Pergunta", placeholder="Ex.: Que prêmio recebeu quem criou a linguagem que influenciou o C++?")
    enviar = st.form_submit_button("Enviar pergunta", type="primary")

if enviar:
    if not pergunta.strip():
        st.warning("Digite uma pergunta antes de enviar.")
    else:
        try:
            with st.spinner("Consultando o sistema..."):
                resultado = responder(pergunta.strip(), modo)
            st.session_state["resultado_consulta"] = resultado
        except (FileNotFoundError, ValueError, RuntimeError) as erro:
            st.session_state.pop("resultado_consulta", None)
            st.error(f"Não foi possível concluir a consulta: {erro}")
        except Exception as erro:
            st.session_state.pop("resultado_consulta", None)
            st.error(f"Ocorreu um erro inesperado: {erro}")

if "resultado_consulta" in st.session_state:
    resultado = st.session_state["resultado_consulta"]
    st.success("Consulta concluída.")
    st.subheader("Resposta")
    st.write(resultado.get("resposta") or "Resposta não fornecida.")
    st.caption("Referências como [C1] e [F1] são detalhadas nos painéis abaixo.")

    st.subheader("Subgrafo interativo")
    exibir_grafo(resultado.get("subgrafo") or {}, resultado.get("caminhos") or [])
    exibir_paineis(resultado, demonstracao=(FONTE_DADOS == "json"))
    if FONTE_DADOS == "json":
        st.info("Demonstração com JSON estático: a resposta não foi consultada no Neo4j nem gerada por um backend real.")

st.divider()
st.caption("Interface GraphRAG/KAG — G2, G3 e G4. Grafo: streamlit-agraph (vis-network).")
