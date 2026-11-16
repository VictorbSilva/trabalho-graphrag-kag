"""Ingestor de comando único (src/banco/ingestor.py, issue #12).

A validação não precisa do banco. Os testes de ingestão usam vetores falsos no
lugar do modelo de embeddings e ids prefixados por teste::, apagados no final.
"""

import copy
import json
import random
from pathlib import Path

import pytest
from neo4j.exceptions import Neo4jError

from conftest import PREFIXO, RAIZ, carregar_semente, com_prefixo
from src.banco.ingestor import (
    carregar_dominio,
    contar,
    ingerir_artigo,
    ingerir_pasta,
    main,
    texto_da_entidade,
    validar_artigo,
)

DOMINIO = carregar_dominio()
DIMENSOES = DOMINIO["embedding"]["dimensoes"]
CONTAGENS_DA_SEMENTE = {"documentos": 4, "trechos": 12, "entidades": 13, "relacoes": 19}


def vetores_falsos(textos):
    return [[1.0] + [0.0] * (DIMENSOES - 1) for _ in textos]


def vetores_distintos(textos):
    """Um vetor diferente por texto, sempre o mesmo para o mesmo texto (para a busca por cosseno)."""
    vetores = []
    for texto in textos:
        sorteio = random.Random(texto)
        vetores.append([sorteio.gauss(0, 1) for _ in range(DIMENSOES)])
    return vetores


def artigo_c() -> dict:
    return copy.deepcopy(carregar_semente()["c.json"])


def gravar(pasta: Path, nome: str, conteudo) -> None:
    texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False)
    (pasta / nome).write_text(texto, encoding="utf-8")


def pasta_com_a_semente(tmp_path: Path) -> Path:
    """Cópia de data/semente/ numa pasta temporária (os ids recebem o prefixo na ingestão)."""
    for nome, artigo in carregar_semente().items():
        gravar(tmp_path, nome, artigo)
    return tmp_path


# ---------- Validação (sem banco) ----------

@pytest.mark.parametrize(
    "caminho",
    sorted((RAIZ / "data" / "semente").glob("*.json"))
    + sorted((RAIZ / "data" / "processado" / "extraido").glob("*.json"))
    + sorted((RAIZ / "data" / "processado" / "curado").glob("*.json")),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_semente_e_artigos_processados_sao_validos(caminho):
    assert validar_artigo(json.loads(caminho.read_text(encoding="utf-8")), DOMINIO) == []


def _sem_documento(a):
    del a["documento"]


def _tipo_de_entidade_fora(a):
    a["entidades"][0]["type"] = "Cidade"


def _tipo_de_relacao_fora(a):
    a["relacoes"][0]["tipo"] = "MORA_EM"


def _direcao_invertida(a):
    r = a["relacoes"][0]  # Dennis Ritchie CRIOU C
    r["origem"], r["destino"] = r["destino"], r["origem"]


def _trecho_inexistente(a):
    a["relacoes"][0]["chunk_id"] = "c#99"


def _id_sem_prefixo_do_tipo(a):
    a["entidades"][0]["id"] = "pessoa:c"


def _trecho_repetido(a):
    a["chunks"][1]["id"] = a["chunks"][0]["id"]


def _index_nao_inteiro(a):
    a["chunks"][0]["index"] = "0"


@pytest.mark.parametrize(
    ("estragar", "trecho_do_erro"),
    [
        (_sem_documento, "falta a chave 'documento'"),
        (_tipo_de_entidade_fora, "tipo 'Cidade' fora do schema"),
        (_tipo_de_relacao_fora, "tipo 'MORA_EM' fora do schema"),
        (_direcao_invertida, "direção fora do schema"),
        (_trecho_inexistente, "chunk_id 'c#99' não existe"),
        (_id_sem_prefixo_do_tipo, "deveria começar com 'tecnologia:'"),
        (_trecho_repetido, "repetido"),
        (_index_nao_inteiro, "index precisa ser um número inteiro"),
    ],
    ids=lambda v: v.__name__.strip("_") if callable(v) else None,
)
def test_validacao_aponta_o_problema(estragar, trecho_do_erro):
    artigo = artigo_c()
    estragar(artigo)
    erros = validar_artigo(artigo, DOMINIO)
    assert any(trecho_do_erro in e for e in erros), erros


# ---------- Texto do embedding da entidade (sem banco) ----------

def test_texto_da_entidade_junta_nome_e_descricao():
    entidade = {"name": "Dennis Ritchie", "description": "cientista da computação"}
    assert texto_da_entidade(entidade) == "Dennis Ritchie. cientista da computação"


@pytest.mark.parametrize("descricao", [None, ""])
def test_texto_da_entidade_sem_descricao_e_so_o_nome(descricao):
    assert texto_da_entidade({"name": "Dennis Ritchie", "description": descricao}) == "Dennis Ritchie"


# ---------- Ingestão (com banco) ----------

def test_ingerir_duas_vezes_nao_muda_as_contagens(banco, tmp_path):
    pasta = pasta_com_a_semente(tmp_path)
    primeira = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    segunda = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert primeira.contagens == segunda.contagens == CONTAGENS_DA_SEMENTE
    assert sorted(segunda.ingeridos) == sorted(carregar_semente())
    assert segunda.invalidos == {}


def test_todo_trecho_recebe_embedding_do_tamanho_do_indice(banco, tmp_path):
    ingerir_pasta(banco, pasta_com_a_semente(tmp_path), prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    registros, _, _ = banco.execute_query(
        "MATCH (c:Chunk) WHERE c.id STARTS WITH $p RETURN size(c.embedding) AS dim", p=PREFIXO
    )
    assert [r["dim"] for r in registros] == [DIMENSOES] * CONTAGENS_DA_SEMENTE["trechos"]


def test_toda_entidade_recebe_embedding_do_tamanho_do_indice(banco, tmp_path):
    ingerir_pasta(banco, pasta_com_a_semente(tmp_path), prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    registros, _, _ = banco.execute_query(
        "MATCH (e:Entity) WHERE e.id STARTS WITH $p RETURN size(e.embedding) AS dim", p=PREFIXO
    )
    assert [r["dim"] for r in registros] == [DIMENSOES] * CONTAGENS_DA_SEMENTE["entidades"]


def test_indice_entity_embedding_encontra_a_propria_entidade(banco, tmp_path):
    ingerir_pasta(banco, pasta_com_a_semente(tmp_path), prefixo=PREFIXO, gerar_vetores=vetores_distintos)
    alvo = PREFIXO + "pessoa:dennis_ritchie"
    registros, _, _ = banco.execute_query(
        """MATCH (alvo:Entity {id: $id})
           CALL db.index.vector.queryNodes('entity_embedding', 1, alvo.embedding)
           YIELD node
           RETURN node.id AS id""",
        id=alvo,
    )
    assert [r["id"] for r in registros] == [alvo]


def test_ingerir_duas_vezes_mantem_o_embedding_das_entidades(banco, tmp_path):
    pasta = pasta_com_a_semente(tmp_path)
    primeira = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    segunda = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert primeira.contagens == segunda.contagens == CONTAGENS_DA_SEMENTE
    registros, _, _ = banco.execute_query(
        "MATCH (e:Entity {id: $id}) RETURN size(e.embedding) AS dim", id=PREFIXO + "pessoa:dennis_ritchie"
    )
    assert registros[0]["dim"] == DIMENSOES


def test_vetor_de_tamanho_errado_para_as_entidades_nao_grava_o_artigo(banco, tmp_path):
    artigo = artigo_c()
    gravar(tmp_path, "c.json", artigo)
    textos_das_entidades = {texto_da_entidade(e) for e in artigo["entidades"]}

    def certo_para_trechos_errado_para_entidades(textos):
        de_entidades = bool(textos) and all(t in textos_das_entidades for t in textos)
        tamanho = DIMENSOES - 1 if de_entidades else DIMENSOES
        return [[1.0] + [0.0] * (tamanho - 1) for _ in textos]

    with pytest.raises(ValueError, match="entidade"):
        ingerir_pasta(banco, tmp_path, prefixo=PREFIXO, gerar_vetores=certo_para_trechos_errado_para_entidades)
    assert contar(banco, PREFIXO) == {"documentos": 0, "trechos": 0, "entidades": 0, "relacoes": 0}


def test_arquivo_invalido_nao_entra_e_os_outros_entram(banco, tmp_path):
    pasta = pasta_com_a_semente(tmp_path)
    quebrado = artigo_c()
    quebrado["documento"]["id"] = "quebrado"
    quebrado["entidades"][0]["type"] = "Cidade"
    gravar(pasta, "quebrado.json", quebrado)
    gravar(pasta, "mal_formado.json", "{ isto não é json")

    resultado = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)

    assert set(resultado.invalidos) == {"quebrado.json", "mal_formado.json"}
    assert len(resultado.ingeridos) == 4
    assert resultado.contagens == CONTAGENS_DA_SEMENTE
    registros, _, _ = banco.execute_query(
        "MATCH (d:Document {id: $id}) RETURN count(d) AS total", id=PREFIXO + "quebrado"
    )
    assert registros[0]["total"] == 0


def test_manifesto_e_ignorado(banco, tmp_path):
    pasta = pasta_com_a_semente(tmp_path)
    gravar(pasta, "manifesto_chunks.json", [{"chunk_id": "x", "origem": "x.txt"}])
    resultado = ingerir_pasta(banco, pasta, prefixo=PREFIXO, gerar_vetores=vetores_falsos)
    assert resultado.ignorados == ["manifesto_chunks.json"]
    assert resultado.invalidos == {}


def test_falha_no_meio_nao_deixa_o_artigo_pela_metade(banco):
    """Uma transação por artigo: se o Neo4j recusa um comando, nada do artigo fica gravado."""
    artigo = com_prefixo(artigo_c(), PREFIXO)
    artigo["relacoes"][-1]["tipo"] = ""  # tipo vazio passa direto pela validação e o Neo4j recusa
    with pytest.raises(Neo4jError):
        ingerir_artigo(banco, artigo)
    assert contar(banco, PREFIXO) == {"documentos": 0, "trechos": 0, "entidades": 0, "relacoes": 0}


def test_comando_imprime_as_contagens_e_sai_com_zero(banco, tmp_path, capsys):
    codigo = main([str(pasta_com_a_semente(tmp_path)), "--prefixo", PREFIXO], gerar_vetores=vetores_falsos)
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "ok        c.json" in saida
    assert "4 documentos, 12 trechos, 13 entidades e 19 relações entre entidades" in saida


def test_comando_sai_com_um_quando_ha_arquivo_invalido(banco, tmp_path, capsys):
    pasta = pasta_com_a_semente(tmp_path)
    gravar(pasta, "quebrado.json", {"documento": {}})
    codigo = main([str(pasta), "--prefixo", PREFIXO], gerar_vetores=vetores_falsos)
    saida = capsys.readouterr().out
    assert codigo == 1
    assert "INVÁLIDO  quebrado.json" in saida
