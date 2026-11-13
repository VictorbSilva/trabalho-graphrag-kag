"""Configuração da API, lida das variáveis de ambiente (arquivo .env na raiz)."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

# JSON de exemplo do contrato da resposta (issue #2).
ARQUIVO_EXEMPLO = RAIZ / "data" / "exemplo_resposta.json"

# De onde vem a resposta:
#   exemplo      devolve o JSON de exemplo (PE1, não precisa de banco nem de LLM)
#   recuperacao  chama a função indicada em API_RESPONDER (PE2)
FONTE = os.getenv("API_FONTE", "exemplo").strip().lower()

# Função de recuperação no formato "modulo:funcao", usada quando FONTE=recuperacao.
RESPONDER = os.getenv("API_RESPONDER", "").strip()

# Tempo limite, em segundos, para a recuperação responder.
TIMEOUT_S = float(os.getenv("API_TIMEOUT_S", "60"))

# Origens liberadas no CORS, separadas por vírgula (padrão: Streamlit local).
CORS_ORIGENS = [
    origem.strip()
    for origem in os.getenv(
        "API_CORS_ORIGENS", "http://localhost:8501,http://127.0.0.1:8501"
    ).split(",")
    if origem.strip()
]
