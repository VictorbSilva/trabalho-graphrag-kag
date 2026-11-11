"""Interface inicial do projeto GraphRAG/KAG - entregas G1 e G2."""

import streamlit as st

from src.interface.config import FONTE_DADOS
from src.interface.servico import responder

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
                resultado = responder(pergunta.strip(), modo)

            st.success("Consulta concluída.")
            st.subheader("Resposta")
            st.write(resultado["resposta"])

            confianca = resultado["confianca"]
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
                st.metric("Modo utilizado", resultado["modo"].upper())

            st.caption(f"Critério de confiança: {criterio}")

            with st.expander("Ver caminhos e referências"):
                for caminho in resultado.get("caminhos", []):
                    st.markdown(f"**Caminho {caminho.get('id', '')}**")
                    st.write(" → ".join(caminho.get("nos", [])))
                    st.write("Relações:", ", ".join(caminho.get("relacoes", [])))

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

                st.markdown("**Subgrafo recebido (dados)**")
                subgrafo = resultado.get("subgrafo", {})
                st.write(f" nós: {len(subgrafo.get('nos', []))}")
                st.write(f" arestas: {len(subgrafo.get('arestas', []))}")
                st.json(subgrafo)

            avisos = resultado.get("avisos", [])
            if avisos:
                st.subheader("Avisos")
                for aviso in avisos:
                    st.warning(str(aviso))

            if FONTE_DADOS == "json":
                st.info(
                    "Demonstração com JSON estático. A resposta não foi consultada "
                    "no Neo4j nem gerada pelo backend real."
                )

        except FileNotFoundError as erro:
            st.error(str(erro))
        except (ValueError, RuntimeError) as erro:
            st.error(f"Não foi possível concluir a consulta: {erro}")
        except Exception as erro:
            st.error(f"Ocorreu um erro inesperado: {erro}")

st.divider()
st.caption(
    "Versão inicial da interface — contrato de resposta C3/C4. "
    "A visualização interativa do subgrafo será implementada na próxima etapa."
)
