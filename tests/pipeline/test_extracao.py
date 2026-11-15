"""Testes da extração (PA3): validação da resposta do modelo, lotes, prompt e cache.

Não usam rede nem chave: o Groq é simulado. Rodam no CI.
"""

import json
from collections import Counter

from src.pipeline import extracao
from src.pipeline.baixar_artigos import gerar_slug

DOMINIO = extracao.carregar_dominio()


def lote(*textos, inicio=0, doc="art"):
    return [{"id": f"{doc}#{inicio + i}", "index": inicio + i, "text": t} for i, t in enumerate(textos)]


def processar(dados, trechos):
    descartes = Counter()
    entidades, relacoes = extracao.processar_resposta(dados, trechos, DOMINIO, descartes)
    return entidades, relacoes, descartes


def test_ids_seguem_a_regra_do_dominio():
    dados = {"entidades": [{"nome": "Dennis Ritchie", "tipo": "Pessoa"}, {"nome": "C++", "tipo": "Tecnologia"},
                           {"nome": "Prêmio Turing", "tipo": "Premio"}, {"nome": "Bell Labs", "tipo": "Organizacao"}]}
    entidades, _, _ = processar(dados, lote("texto"))
    assert set(entidades) == {"pessoa:dennis_ritchie", "tecnologia:c_mais_mais",
                              "premio:premio_turing", "organizacao:bell_labs"}


def test_tipo_fora_do_dominio_e_descartado_e_tipo_sem_acento_e_aceito():
    dados = {"entidades": [{"nome": "Nova Jérsei", "tipo": "Lugar"}, {"nome": "Bell Labs", "tipo": "Organização"}]}
    entidades, _, descartes = processar(dados, lote("Bell Labs fica em Nova Jérsei."))
    assert list(entidades) == ["organizacao:bell_labs"]
    assert descartes["entidade de tipo fora do domínio"] == 1


def test_relacao_valida_aponta_para_o_trecho_certo():
    trechos = lote("Dennis Ritchie criou o C.", "Ritchie trabalhou nos Bell Labs.", inicio=4)
    dados = {"entidades": [{"nome": "Dennis Ritchie", "tipo": "Pessoa"}, {"nome": "C", "tipo": "Tecnologia"}],
             "relacoes": [{"origem": "Dennis Ritchie", "tipo": "CRIOU", "destino": "C", "trecho": 4}]}
    entidades, relacoes, _ = processar(dados, trechos)
    assert relacoes == {("pessoa:dennis_ritchie", "CRIOU", "tecnologia:c", "art#4")}
    assert "art#4" in entidades["pessoa:dennis_ritchie"]["chunk_ids"]


def test_direcao_invertida_e_corrigida():
    dados = {"entidades": [{"nome": "Dennis Ritchie", "tipo": "Pessoa"}, {"nome": "Prêmio Turing", "tipo": "Premio"}],
             "relacoes": [{"origem": "Prêmio Turing", "tipo": "RECEBEU", "destino": "Dennis Ritchie", "trecho": 0}]}
    _, relacoes, descartes = processar(dados, lote("Ritchie recebeu o Prêmio Turing."))
    assert relacoes == {("pessoa:dennis_ritchie", "RECEBEU", "premio:premio_turing", "art#0")}
    assert descartes["relação corrigida (direção invertida)"] == 1


def test_relacao_fora_do_dominio_ou_com_tipos_incompativeis_e_descartada():
    dados = {"entidades": [{"nome": "Dennis Ritchie", "tipo": "Pessoa"}, {"nome": "Ken Thompson", "tipo": "Pessoa"}],
             "relacoes": [{"origem": "Dennis Ritchie", "tipo": "AMIGO_DE", "destino": "Ken Thompson", "trecho": 0},
                          {"origem": "Dennis Ritchie", "tipo": "CRIOU", "destino": "Ken Thompson", "trecho": 0}]}
    _, relacoes, descartes = processar(dados, lote("Ritchie e Thompson."))
    assert relacoes == set()
    assert descartes["relação fora do domínio"] == 1
    assert descartes["relação com tipos incompatíveis"] == 1


def test_entidade_ausente_e_criada_quando_o_tipo_so_pode_ser_um():
    # RECEBEU: Pessoa -> Premio, os dois lados têm um único tipo possível.
    dados = {"entidades": [],
             "relacoes": [{"origem": "Ken Thompson", "tipo": "RECEBEU", "destino": "Prêmio Turing", "trecho": 0}]}
    entidades, relacoes, _ = processar(dados, lote("Ken Thompson recebeu o Prêmio Turing."))
    assert set(entidades) == {"pessoa:ken_thompson", "premio:premio_turing"}
    assert len(relacoes) == 1


def test_entidade_ausente_com_tipo_ambiguo_derruba_a_relacao():
    # CRIOU: Pessoa -> Tecnologia ou Organizacao; o destino não dá para adivinhar.
    dados = {"entidades": [{"nome": "Dennis Ritchie", "tipo": "Pessoa"}],
             "relacoes": [{"origem": "Dennis Ritchie", "tipo": "CRIOU", "destino": "Unix", "trecho": 0}]}
    _, relacoes, descartes = processar(dados, lote("Ritchie criou o Unix."))
    assert relacoes == set()
    assert descartes["relação com entidade ausente"] == 1


def test_trecho_invalido_cai_no_trecho_onde_os_dois_nomes_aparecem():
    trechos = lote("Texto sem nomes.", "Guido van Rossum criou o Python.", inicio=7)
    dados = {"entidades": [{"nome": "Guido van Rossum", "tipo": "Pessoa"}, {"nome": "Python", "tipo": "Tecnologia"}],
             "relacoes": [{"origem": "Guido van Rossum", "tipo": "CRIOU", "destino": "Python", "trecho": 99}]}
    _, relacoes, _ = processar(dados, trechos)
    assert relacoes == {("pessoa:guido_van_rossum", "CRIOU", "tecnologia:python", "art#8")}


def test_resposta_malformada_nao_derruba():
    entidades, relacoes, descartes = processar({"entidades": ["x", None, {"tipo": "Pessoa"}], "relacoes": [1]}, lote("t"))
    assert entidades == {} and relacoes == set()
    assert sum(descartes.values()) == 4


def test_extrair_json_tolera_cerca_de_codigo_e_texto_em_volta():
    assert extracao.extrair_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extracao.extrair_json('Aqui está: {"a": 1} Pronto.') == {"a": 1}


def test_lotes_respeitam_quantidade_e_tamanho():
    chunks = [{"id": f"a#{i}", "index": i, "text": "x" * 450} for i in range(7)]
    lotes = extracao.montar_lotes(chunks, por_lote=3, limite_caracteres=1400)
    assert [len(l) for l in lotes] == [3, 3, 1]
    assert [c["index"] for l in lotes for c in l] == list(range(7))
    assert [len(l) for l in extracao.montar_lotes(chunks, por_lote=5, limite_caracteres=1000)] == [2, 2, 2, 1]


def test_prompt_traz_todos_os_tipos_e_relacoes_do_dominio():
    prompt = extracao.construir_prompt(DOMINIO)
    for rotulo in DOMINIO["rotulos"]:
        assert rotulo["nome"] in prompt
    for relacao in DOMINIO["relacoes"]:
        assert relacao["tipo"] in prompt
    assert "[TN]" in prompt


def test_cache_muda_com_o_texto_o_modelo_e_o_prompt():
    a = extracao.chave_do_cache("m", "T", lote("um"), None)
    assert a == extracao.chave_do_cache("m", "T", lote("um"), None)
    assert a != extracao.chave_do_cache("m", "T", lote("dois"), None)
    assert a != extracao.chave_do_cache("outro", "T", lote("um"), None)
    assert a != extracao.chave_do_cache("m", "T", lote("um"), "low")


def test_artigo_inteiro_com_groq_simulado_e_cache(tmp_path, monkeypatch):
    chunks = [{"id": f"python#{i}", "index": i, "text": t} for i, t in enumerate(
        ["O Python foi concebido por Guido van Rossum.", "Guido van Rossum trabalhou no CWI.", "Mais um trecho."])]
    (tmp_path / "chunks").mkdir()
    (tmp_path / "chunks" / "python.json").write_text(json.dumps(
        {"documento": {"id": "python", "title": "Python", "source": "https://exemplo"}, "chunks": chunks}), encoding="utf-8")
    monkeypatch.setattr(extracao, "CHUNKS", tmp_path / "chunks")
    monkeypatch.setattr(extracao, "SAIDA", tmp_path / "extraido")
    monkeypatch.setattr(extracao, "CACHE", tmp_path / "cache")

    chamadas = []

    def groq_falso(modelo, mensagens, **opcoes):
        chamadas.append(modelo)
        conteudo = json.dumps({
            "entidades": [{"nome": "Guido van Rossum", "tipo": "Pessoa", "trechos": [0, 1]},
                          {"nome": "Python", "tipo": "Tecnologia", "trechos": [0]},
                          {"nome": "CWI", "tipo": "Organizacao", "trechos": [1]}],
            "relacoes": [{"origem": "Guido van Rossum", "tipo": "CRIOU", "destino": "Python", "trecho": 0},
                         {"origem": "Guido van Rossum", "tipo": "TRABALHOU_EM", "destino": "CWI", "trecho": 1}]})
        return {"choices": [{"message": {"content": conteudo}}], "usage": {"total_tokens": 100}}, {}

    monkeypatch.setattr(extracao, "conversar", groq_falso)
    argumentos = extracao.argparse.Namespace(max_chunks=20, lote=3, modelo="m", esforco=None)
    estat = Counter()
    resumo = extracao.processar_artigo("python", argumentos, DOMINIO, "prompt", extracao.Ritmo(), estat)

    assert resumo["entidades"] == 3 and resumo["relacoes"] == 2
    saida = json.loads((tmp_path / "extraido" / "python.json").read_text(encoding="utf-8"))
    assert set(saida) == {"documento", "chunks", "entidades", "relacoes"}
    assert len(saida["chunks"]) == 3
    assert {"origem", "destino", "tipo", "chunk_id"} == set(saida["relacoes"][0])
    assert {"id", "name", "type", "aliases", "description", "chunk_ids"} == set(saida["entidades"][0])
    assert len(chamadas) == 1 and estat["chamadas_ao_groq"] == 1

    extracao.processar_artigo("python", argumentos, DOMINIO, "prompt", extracao.Ritmo(), estat)
    assert len(chamadas) == 1 and estat["chamadas_do_cache"] == 1   # segunda rodada não chama o Groq


def test_slug_usado_nos_ids_e_o_mesmo_do_download():
    assert gerar_slug("C++") == "c_mais_mais"
    assert gerar_slug("Java (linguagem de programação)") == "java"
