"""Chamada real ao LLM da Abacus RouteLLM (src/recuperacao/llm.py, issue V4).

Precisa de ABACUS_API_KEY e ABACUS_MODELO no .env. Sem a chave, o teste é pulado
(tests/conftest.py).
"""

import pytest

from src.recuperacao.llm import gerar_texto

pytestmark = pytest.mark.llm


def test_gerar_texto_devolve_texto():
    texto = gerar_texto([{"role": "user", "content": "Responda só: ok"}])
    assert isinstance(texto, str)
    assert texto.strip()
