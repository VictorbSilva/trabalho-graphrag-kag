"""Testes da exportação da avaliação para o Hugging Face Datasets.

Leem só os arquivos de data/avaliacao/ e gravam em tmp_path: não precisam de banco,
de LLM nem do modelo de embeddings, então rodam no CI.
"""

import json

import pytest

from src.avaliacao import exportar_hf
from src.avaliacao.exportar_hf import (
    CAMPOS_PERGUNTA,
    CAMPOS_RESPOSTA,
    CLASSES,
    MODELO_LLM,
    exportar,
    exportar_perguntas,
    exportar_respostas,
)

BANCOS = {"semente", "completo"}
MODOS = {"vetorial", "graphrag"}
TIPOS = {"um_salto", "multi_hop", "sem_resposta"}


@pytest.fixture(scope="module")
def perguntas():
    return exportar_perguntas()


@pytest.fixture(scope="module")
def respostas():
    return exportar_respostas()


# --- quantidades -------------------------------------------------------------

def test_existem_15_perguntas(perguntas):
    assert len(perguntas) == 15
    assert len({p["id"] for p in perguntas}) == 15


def test_existem_60_respostas_classificadas(respostas):
    # 15 perguntas x 2 modos x 2 bancos
    assert len(respostas) == 60
    assert len({(r["id_pergunta"], r["banco"], r["modo"]) for r in respostas}) == 60
    assert all(r["classificacao"] in CLASSES for r in respostas)


def test_cada_banco_e_modo_tem_as_15_perguntas(respostas):
    for banco in BANCOS:
        for modo in MODOS:
            grupo = [r for r in respostas if r["banco"] == banco and r["modo"] == modo]
            assert len(grupo) == 15, (banco, modo)


# --- campos ------------------------------------------------------------------

def test_toda_pergunta_tem_os_campos_esperados(perguntas):
    for p in perguntas:
        assert list(p) == list(CAMPOS_PERGUNTA), p["id"]
        assert p["tipo"] in TIPOS
        assert isinstance(p["pergunta"], str) and p["pergunta"]
        assert isinstance(p["resposta_esperada"], str) and p["resposta_esperada"]
        assert isinstance(p["saltos"], int)
        for tripla in p["caminho_esperado"]:
            assert set(tripla) == {"origem", "tipo", "destino"}
        for evidencia in p["evidencias"]:
            assert isinstance(evidencia["trecho"], str) and evidencia["trecho"]


def test_toda_resposta_tem_os_campos_esperados(respostas):
    for r in respostas:
        assert list(r) == list(CAMPOS_RESPOSTA), r["id_pergunta"]
        assert r["banco"] in BANCOS
        assert r["modo"] in MODOS
        assert r["modelo_llm"] == MODELO_LLM[r["banco"]]
        assert isinstance(r["resposta"], str) and r["resposta"]
        for trecho in r["trechos"]:
            assert set(trecho) == {"id", "chunk_id", "documento", "url", "trecho", "score"}
        for caminho in r["caminhos"]:
            assert set(caminho) == {"id", "nos", "relacoes", "fontes"}
            assert len(caminho["relacoes"]) == len(caminho["nos"]) - 1


def test_modo_vetorial_nao_tem_caminhos(respostas):
    assert all(r["caminhos"] == [] for r in respostas if r["modo"] == "vetorial")


# --- integridade -------------------------------------------------------------

def test_toda_resposta_aponta_para_uma_pergunta_que_existe(perguntas, respostas):
    ids = {p["id"] for p in perguntas}
    assert {r["id_pergunta"] for r in respostas} <= ids


def test_resposta_de_pergunta_inexistente_levanta_erro(tmp_path):
    respostas = [{"id": "P99", "modo": "vetorial", "erro": None, "resposta": {}}]
    arquivo = tmp_path / "respostas.json"
    arquivo.write_text(json.dumps(respostas), encoding="utf-8")
    classes = tmp_path / "classificacao.json"
    classes.write_text(json.dumps({"P99": {"vetorial": "correta"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="P99"):
        exportar_respostas(rodadas={"semente": (arquivo, classes)})


def test_resposta_sem_classificacao_levanta_erro(tmp_path):
    original = exportar_hf.RODADAS["semente"]
    classes = tmp_path / "classificacao.json"
    classes.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="classifica"):
        exportar_respostas(rodadas={"semente": (original[0], classes)})


def test_contagens_por_classe_batem_com_os_docs(respostas):
    # Tabelas de docs/avaliacao-resultados.md e docs/avaliacao-resultados-completo.md
    def contar(banco, modo, classe):
        return sum(1 for r in respostas if (r["banco"], r["modo"], r["classificacao"]) == (banco, modo, classe))

    assert contar("semente", "vetorial", "correta") == 4
    assert contar("semente", "graphrag", "correta") == 5
    assert contar("completo", "vetorial", "correta") == 6
    assert contar("completo", "graphrag", "correta") == 10
    assert contar("completo", "graphrag", "alucinada") == 1
    assert sum(1 for r in respostas if r["classificacao"] == "alucinada") == 1


# --- arquivos gravados -------------------------------------------------------

def _ler_jsonl(caminho):
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines()]


def test_exportar_grava_os_dois_jsonl_e_o_card(tmp_path):
    exportar(tmp_path)
    assert len(_ler_jsonl(tmp_path / "perguntas.jsonl")) == 15
    assert len(_ler_jsonl(tmp_path / "respostas.jsonl")) == 60
    assert (tmp_path / "README.md").read_text(encoding="utf-8").startswith("---\n")


def test_jsonl_mantem_os_acentos(tmp_path):
    exportar(tmp_path)
    texto = (tmp_path / "perguntas.jsonl").read_text(encoding="utf-8")
    assert "\\u00" not in texto
    assert "linguagem de programação" in texto


def test_arquivos_gravados_com_lf_mesmo_com_card_em_crlf(tmp_path, monkeypatch):
    # No Windows, com core.autocrlf, o card sai do checkout com CRLF.
    card_crlf = tmp_path / "card.md"
    card_crlf.write_bytes(exportar_hf.ARQUIVO_CARD.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    monkeypatch.setattr(exportar_hf, "ARQUIVO_CARD", card_crlf)
    saida = tmp_path / "saida"
    exportar(saida)
    for nome in ("perguntas.jsonl", "respostas.jsonl", "README.md"):
        assert b"\r" not in (saida / nome).read_bytes(), nome


def test_nenhum_caminho_local_vai_para_o_dataset(tmp_path):
    exportar(tmp_path)
    for nome in ("perguntas.jsonl", "respostas.jsonl", "README.md"):
        texto = (tmp_path / nome).read_text(encoding="utf-8")
        for proibido in ("/home/", "/Users/", "C:\\", ".env"):
            assert proibido not in texto, (nome, proibido)


# --- dataset card ------------------------------------------------------------

def _cabecalho(card: str) -> str:
    _, cabecalho, _ = card.split("---\n", 2)
    return cabecalho


def test_card_tem_o_cabecalho_do_hugging_face(tmp_path):
    exportar(tmp_path)
    cabecalho = _cabecalho((tmp_path / "README.md").read_text(encoding="utf-8"))
    for linha in (
        "license: cc-by-sa-4.0",
        "- pt",
        "- question-answering",
        "- rag",
        "- graphrag",
        "- knowledge-graph",
        "- hallucination-evaluation",
        "- n<1K",
    ):
        assert linha in cabecalho, linha
    # os dois arquivos aparecem como configurações separadas na pré-visualização
    assert "path: perguntas.jsonl" in cabecalho
    assert "path: respostas.jsonl" in cabecalho


def test_card_sem_travessoes(tmp_path):
    exportar(tmp_path)
    card = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "\u2014" not in card and "\u2013" not in card
