"""Tipo de entidade que a pergunta pede como resposta (issue V3).

Olha só o começo da pergunta: "Quem ..." pede uma Pessoa e "Que prêmio ...",
"Qual organização ...", "Quais linguagens ..." pedem o tipo da palavra depois
de que/qual/quais. Os tipos são os rótulos de neo4j/dominio.json. A expansão
multi-hop usa o tipo só para ordenar os caminhos, nunca para filtrar.
"""

import re
import unicodedata

PALAVRAS_POR_TIPO = {
    "Premio": {"premio", "premios", "medalha", "medalhas", "distincao", "distincoes", "premiacao"},
    "Pessoa": {
        "pessoa", "pessoas", "cientista", "cientistas", "programador", "programadores",
        "engenheiro", "engenheiros", "criador", "criadores", "inventor", "inventores",
        "fundador", "fundadores",
    },
    "Organizacao": {
        "organizacao", "organizacoes", "empresa", "empresas", "laboratorio", "laboratorios",
        "universidade", "universidades", "instituicao", "instituicoes", "instituto", "institutos",
    },
    "Tecnologia": {
        "linguagem", "linguagens", "tecnologia", "tecnologias", "sistema", "sistemas",
        "computador", "computadores", "protocolo", "protocolos", "algoritmo", "algoritmos",
    },
}

_PREPOSICAO = r"(?:(?:em|de|da|do|por|para|com)\s+)?"
_QUEM = re.compile(rf"^{_PREPOSICAO}quem\b")
_QUE_QUAL = re.compile(rf"^{_PREPOSICAO}(?:que|qual|quais)\s+(\w+)")


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos."""
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()


def tipo_esperado(pergunta: str) -> str | None:
    """O rótulo do domínio que a pergunta pede, ou None se o começo não indica um."""
    texto = _normalizar(pergunta).strip()
    if _QUEM.match(texto):
        return "Pessoa"
    encontrado = _QUE_QUAL.match(texto)
    if encontrado:
        palavra = encontrado.group(1)
        for tipo, palavras in PALAVRAS_POR_TIPO.items():
            if palavra in palavras:
                return tipo
    return None
