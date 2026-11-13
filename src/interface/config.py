"""Configurações da interface GraphRAG/KAG.

Para trocar o JSON de demonstração pela API do Pedro, altere FONTE_DADOS
para "api" e configure API_URL no ambiente (.env).
"""

from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[2]
ARQUIVO_EXEMPLO = ROOT_DIR / "data" / "exemplo_resposta.json"

FONTE_DADOS = os.getenv("FONTE_DADOS", "json").strip().lower()
API_URL = os.getenv("API_URL", "http://localhost:8000/perguntar")
