"""Painéis de explicabilidade da resposta GraphRAG/KAG (G4)."""
import re
import streamlit as st


def _lista(valor):
    return valor if isinstance(valor, list) else []


def _texto(valor, padrao="Não informado"):
    return str(valor) if valor is not None and str(valor).strip() else padrao


def _refs(texto):
    return sorted(set(re.findall(r"\[([CF]\d+)\]", str(texto))))


def exibir_paineis(resultado: dict, demonstracao: bool = False) -> None:
    st.subheader("Painéis de explicabilidade")
    caminhos = [x for x in _lista(resultado.get("caminhos")) if isinstance(x, dict)]
    fontes = [x for x in _lista(resultado.get("fontes")) if isinstance(x, dict)]
    nos = _lista(resultado.get("nos_consultados"))
    confianca = resultado.get("confianca") or {}
    if not isinstance(confianca, dict):
        confianca = {}
    valor = confianca.get("valor")
    nivel = _texto(confianca.get("nivel"))
    col1, col2, col3 = st.columns(3)
    with col1:
        if isinstance(valor, (int, float)) and not isinstance(valor, bool) and 0 <= valor <= 1:
            st.metric("Confiança" + (" (exemplo)" if demonstracao else ""), f"{valor:.0%}")
        else:
            st.metric("Confiança", "Não informada")
    with col2:
        st.metric("Nível", nivel.capitalize())
    with col3:
        st.metric("Modo", _texto(resultado.get("modo")).upper())
    st.caption("Critério: " + _texto(confianca.get("criterio"), "Critério não informado."))
    st.caption("A confiança é um valor fornecido pela resposta; não representa garantia de correção.")

    refs = _refs(resultado.get("resposta", ""))
    ids_caminhos = {str(c.get("id")) for c in caminhos}
    ids_fontes = {str(f.get("id")) for f in fontes}
    if refs:
        st.write("Referências citadas na resposta: " + ", ".join(f"[{r}]" for r in refs))
        ausentes = [r for r in refs if r not in (ids_caminhos if r.startswith("C") else ids_fontes)]
        if ausentes:
            st.warning("Referências sem item correspondente: " + ", ".join(f"[{r}]" for r in ausentes))

    aba_caminhos, aba_nos, aba_cypher, aba_fontes = st.tabs([
        f"Caminhos ({len(caminhos)})", f"Nós consultados ({len(nos)})", "Cypher", f"Fontes ({len(fontes)})"
    ])
    with aba_caminhos:
        if not caminhos:
            st.info("Nenhum caminho foi fornecido.")
        for caminho in caminhos:
            cid = _texto(caminho.get("id"), "Sem ID")
            st.markdown(f"**[{cid}] Caminho citado**")
            st.write(" → ".join(map(str, _lista(caminho.get("nos")))) or "Nós não informados.")
            relacoes = _lista(caminho.get("relacoes"))
            st.caption("Relações: " + (" · ".join(map(str, relacoes)) if relacoes else "Não informadas"))
            chunks = _lista(caminho.get("fontes"))
            if chunks:
                st.caption("Trechos (chunk IDs) associados: " + ", ".join(map(str, chunks)))
            st.divider()
    with aba_nos:
        if not nos:
            st.info("Nenhum nó consultado foi informado.")
        else:
            mapa = {str(n.get("id")): n for n in _lista((resultado.get("subgrafo") or {}).get("nos")) if isinstance(n, dict)}
            for ident in nos:
                item = mapa.get(str(ident), {})
                st.write(f"**{_texto(item.get('nome'), str(ident))}** — ID: `{ident}` — Tipo: {_texto(item.get('tipo'))}")
    with aba_cypher:
        cypher = resultado.get("cypher")
        if cypher:
            st.code(str(cypher), language="cypher")
            st.caption("Consulta exibida somente para leitura. Nenhuma execução é feita por este painel.")
        else:
            st.info("Nenhuma consulta Cypher foi fornecida para esta resposta.")
    with aba_fontes:
        if not fontes:
            st.info("Nenhuma fonte foi fornecida.")
        for fonte in fontes:
            fid = _texto(fonte.get("id"), "Sem ID")
            st.markdown(f"**[{fid}] {_texto(fonte.get('documento'), 'Documento sem título')}**")
            st.write(_texto(fonte.get("trecho"), "Trecho não informado."))
            st.caption("Chunk ID: " + _texto(fonte.get("chunk_id")))
            score = fonte.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                st.caption(f"Score de recuperação: {score:g}")
            url = fonte.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                st.link_button("Abrir fonte", url, key=f"fonte_{fid}")
            st.divider()

    avisos = _lista(resultado.get("avisos"))
    if avisos:
        st.markdown("**Avisos do sistema**")
        for aviso in avisos:
            st.warning(_texto(aviso))
    else:
        st.caption("Nenhum aviso retornado pelo sistema.")
