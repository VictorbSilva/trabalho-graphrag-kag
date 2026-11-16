"""PA3: extrai entidades e relações dos trechos com o Groq, no formato do contrato.

Uso, na raiz do repositório (com GROQ_API_KEY no .env):

    python src/pipeline/extracao.py --dry-run                      # só conta as chamadas e estima o tempo
    python src/pipeline/extracao.py --artigos dennis_ritchie c --max-chunks 8
    python src/pipeline/extracao.py                                # os artigos das perguntas de avaliação
    python src/pipeline/extracao.py --todos --max-chunks 0         # tudo (demora e gasta cota)

Lê data/processado/chunks/<id>.json (saída do chunking) e neo4j/dominio.json (rótulos e relações).
Grava data/processado/extraido/<id>.json no formato do contrato (documento, chunks, entidades, relacoes).
Essa saída ainda tem entidades repetidas entre artigos: a resolução (PA4) junta e grava o arquivo final.

Como funciona:
- Os trechos de cada artigo são agrupados em lotes pequenos (poucos trechos por chamada) para
  gastar menos tokens com o prompt. O limite do Groq é por tokens por minuto, não por chamada.
- Toda resposta fica em .cache/extracao/: rodar de novo não gasta cota com o que já foi feito.
- A resposta do modelo é validada contra o domínio: tipos e relações fora da lista são descartados,
  relações com a direção invertida são corrigidas, e cada relação aponta para o trecho que a sustenta.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, deque
from pathlib import Path

try:  # como pacote (testes) ou como script
    from .baixar_artigos import gerar_slug
    from .groq_cliente import ErroGroq, carregar_env, conversar
except ImportError:
    from baixar_artigos import gerar_slug
    from groq_cliente import ErroGroq, carregar_env, conversar

RAIZ = Path(__file__).resolve().parents[2]
DOMINIO = RAIZ / "neo4j" / "dominio.json"
MANIFESTO = RAIZ / "data" / "bruto" / "manifesto.json"
PERGUNTAS = RAIZ / "data" / "avaliacao" / "perguntas.json"
CHUNKS = RAIZ / "data" / "processado" / "chunks"
SAIDA = RAIZ / "data" / "processado" / "extraido"
CACHE = RAIZ / ".cache" / "extracao"

VERSAO_PROMPT = "3"  # mude ao alterar o prompt: invalida o cache
MODELO_PADRAO = "openai/gpt-oss-120b"
TRECHOS_POR_LOTE = 5
LIMITE_CARACTERES_LOTE = 2400
MAX_TOKENS_RESPOSTA = 2000
REQUISICOES_POR_MINUTO = 28  # o limite medido é 30
TOKENS_POR_MINUTO = 7000     # o limite medido é 8000


# ---------------------------------------------------------------- prompt

def carregar_dominio() -> dict:
    return json.loads(DOMINIO.read_text(encoding="utf-8"))


def construir_prompt(dominio: dict) -> str:
    """Instruções fixas: tipos, relações e regras. Sai do neo4j/dominio.json (fonte única)."""
    tipos = "\n".join(f"- {r['nome']}: {r['descricao']}" for r in dominio["rotulos"])
    relacoes = "\n".join(
        f"- {r['tipo']}: {' ou '.join(r['de'])} -> {' ou '.join(r['para'])}. {r['descricao']}"
        for r in dominio["relacoes"]
    )
    return f"""Você extrai um grafo de conhecimento de trechos de artigos da Wikipédia sobre história da computação.
Responda SOMENTE com um objeto JSON, sem texto fora dele.

Tipos de entidade permitidos:
{tipos}

Relações permitidas (origem -> destino, nesta direção):
{relacoes}

Regras:
1. Extraia apenas o que o texto afirma. Não use conhecimento de fora do texto.
2. Use o nome completo e mais comum da entidade ("Dennis Ritchie", não "Ritchie"); variações vão em "aliases".
3. Expressões como "ele", "a linguagem" ou "a empresa" normalmente se referem ao tema do artigo (veja o título).
4. Ignore o que não for dos tipos acima (datas, cidades, países, livros, eventos).
5. Toda entidade usada em uma relação precisa estar em "entidades".
6. "trecho" é o número do trecho que sustenta o fato, o N de [TN].
7. Sem nada a extrair, devolva listas vazias.
8. CRIOU exige autoria ou criação explicitamente
   sustentada pelo trecho. Nomear, adaptar,
   modificar ou contribuir não significa criar.
9. Quando um trecho mencionar vários criadores
   e várias tecnologias, não atribua automaticamente
   todas as criações a todas as pessoas.
10. Não associe uma relação a um trecho que
    não sustente a afirmação específica.
    Na dúvida, omita a relação.
11. Diferencie criar uma tecnologia de colaborar
    em seu desenvolvimento e de trabalhar na
    organização onde ela foi desenvolvida.
12. INFLUENCIADA_POR aponta sempre da tecnologia
    influenciada para aquela que exerceu influência.
    Exemplo: "C influenciou C++" significa
    C++ -INFLUENCIADA_POR-> C, nunca o contrário.
13. Se o texto afirmar que duas pessoas receberam
    o mesmo prêmio, registre uma relação RECEBEU
    para cada pessoa. Não omita fatos explicitamente
    afirmados e compatíveis com o domínio.
14. Quando houver uma afirmação genérica de criação
    coletiva e outra específica atribuindo a autoria,
    priorize a atribuição específica. Não distribua
    automaticamente todas as criações a todos os autores.
15. Extraia todas as relações claramente sustentadas
    pelo texto, sem sacrificar a cobertura por excesso
    de cautela.

Formato:
{{"entidades": [{{"nome": "...", "tipo": "Pessoa", "aliases": ["..."], "descricao": "uma frase curta", "trechos": [0]}}],
 "relacoes": [{{"origem": "nome", "tipo": "CRIOU", "destino": "nome", "trecho": 0}}]}}

Exemplo. Artigo: John Backus
[T0] John Backus liderou na IBM a equipe que criou o Fortran, uma linguagem de programação. Backus recebeu o Prêmio Turing em 1977.
Resposta:
{{"entidades": [{{"nome": "John Backus", "tipo": "Pessoa", "aliases": ["Backus"], "descricao": "Cientista da computação que liderou a criação do Fortran.", "trechos": [0]}},
 {{"nome": "IBM", "tipo": "Organizacao", "aliases": [], "descricao": "Empresa onde o Fortran foi desenvolvido.", "trechos": [0]}},
 {{"nome": "Fortran", "tipo": "Tecnologia", "aliases": [], "descricao": "Linguagem de programação.", "trechos": [0]}},
 {{"nome": "Prêmio Turing", "tipo": "Premio", "aliases": [], "descricao": "Prêmio da computação.", "trechos": [0]}}],
 "relacoes": [{{"origem": "John Backus", "tipo": "TRABALHOU_EM", "destino": "IBM", "trecho": 0}},
 {{"origem": "John Backus", "tipo": "CRIOU", "destino": "Fortran", "trecho": 0}},
 {{"origem": "Fortran", "tipo": "DESENVOLVIDA_EM", "destino": "IBM", "trecho": 0}},
 {{"origem": "John Backus", "tipo": "RECEBEU", "destino": "Prêmio Turing", "trecho": 0}}]}}"""


def mensagem_do_lote(titulo: str, lote: list[dict]) -> str:
    trechos = "\n".join(f"[T{c['index']}] {c['text']}" for c in lote)
    return f"Artigo: {titulo}\n\n{trechos}"


def montar_lotes(chunks: list[dict], por_lote: int = TRECHOS_POR_LOTE,
                 limite_caracteres: int = LIMITE_CARACTERES_LOTE) -> list[list[dict]]:
    lotes, atual, tamanho = [], [], 0
    for chunk in chunks:
        if atual and (len(atual) >= por_lote or tamanho + len(chunk["text"]) > limite_caracteres):
            lotes.append(atual)
            atual, tamanho = [], 0
        atual.append(chunk)
        tamanho += len(chunk["text"])
    if atual:
        lotes.append(atual)
    return lotes


# ---------------------------------------------------------------- validação da resposta

def normalizar_texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def extrair_json(texto: str) -> dict:
    """Tolera cerca de código (```json) e texto em volta do objeto."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    try:
        dados = json.loads(texto)
    except ValueError:
        inicio, fim = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise
        dados = json.loads(texto[inicio:fim + 1])
    if not isinstance(dados, dict):
        raise ValueError("a resposta não é um objeto JSON")
    return dados


def processar_resposta(dados: dict, lote: list[dict], dominio: dict, descartes: Counter) -> tuple[dict, set]:
    """Valida a resposta de um lote. Devolve (entidades por id, relações).

    Cada relação é (origem_id, tipo, destino_id, chunk_id). Conta em `descartes` o que foi
    corrigido ou jogado fora, para o resumo final.
    """
    prefixos = {r["nome"]: r["prefixo_id"] for r in dominio["rotulos"]}
    tipos = {gerar_slug(nome): nome for nome in prefixos}
    regras = {r["tipo"]: r for r in dominio["relacoes"]}
    ids_dos_trechos = {c["index"]: c["id"] for c in lote}
    textos = {c["index"]: normalizar_texto(c["text"]) for c in lote}
    primeiro = lote[0]["index"]

    entidades: dict[str, dict] = {}
    por_nome: dict[str, list[str]] = {}

    def onde_aparece(nome: str) -> list[int]:
        chave = normalizar_texto(nome)
        return [i for i, t in textos.items() if chave and chave in t]

    def trecho_valido(valor) -> int | None:
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            return None
        return numero if numero in ids_dos_trechos else None

    def registrar(nome: str, tipo: str, aliases=(), descricao: str = "", trechos=()) -> str:
        ident = f"{prefixos[tipo]}:{gerar_slug(nome)}"
        ent = entidades.setdefault(ident, {"id": ident, "name": nome, "type": tipo,
                                           "aliases": set(), "description": "", "chunk_ids": set()})
        ent["aliases"].update(a for a in aliases if a and a != nome)
        if descricao and not ent["description"]:
            ent["description"] = descricao
        ent["chunk_ids"].update(ids_dos_trechos[i] for i in trechos)
        for variante in (nome, *aliases):
            fila = por_nome.setdefault(gerar_slug(variante), [])
            if ident not in fila:
                fila.append(ident)
        return ident

    def achar(nome: str, preferidos: list[str]) -> str | None:
        candidatos = por_nome.get(gerar_slug(nome), [])
        for ident in candidatos:
            if entidades[ident]["type"] in preferidos:
                return ident
        return candidatos[0] if candidatos else None

    for bruto in dados.get("entidades") or []:
        if not isinstance(bruto, dict):
            descartes["entidade malformada"] += 1
            continue
        nome = str(bruto.get("nome") or "").strip()
        tipo = tipos.get(gerar_slug(str(bruto.get("tipo") or "")))
        if not gerar_slug(nome):
            descartes["entidade sem nome"] += 1
            continue
        if tipo is None:
            descartes["entidade de tipo fora do domínio"] += 1
            continue
        aliases = [str(a).strip() for a in (bruto.get("aliases") or []) if isinstance(a, str)]
        trechos = [t for t in (trecho_valido(x) for x in (bruto.get("trechos") or [])) if t is not None]
        trechos = trechos or onde_aparece(nome) or [primeiro]
        registrar(nome, tipo, aliases, str(bruto.get("descricao") or "").strip(), trechos)

    relacoes: set[tuple] = set()
    for bruto in dados.get("relacoes") or []:
        if not isinstance(bruto, dict):
            descartes["relação malformada"] += 1
            continue
        tipo = str(bruto.get("tipo") or "").strip().upper().replace(" ", "_")
        regra = regras.get(tipo)
        if regra is None:
            descartes["relação fora do domínio"] += 1
            continue
        nome_o, nome_d = str(bruto.get("origem") or "").strip(), str(bruto.get("destino") or "").strip()
        if not gerar_slug(nome_o) or not gerar_slug(nome_d):
            descartes["relação sem origem ou destino"] += 1
            continue

        origem, destino = achar(nome_o, regra["de"]), achar(nome_d, regra["para"])
        if origem is None and len(regra["de"]) == 1:   # o tipo só pode ser um: cria a entidade que faltou
            origem = registrar(nome_o, regra["de"][0], trechos=onde_aparece(nome_o) or [primeiro])
        if destino is None and len(regra["para"]) == 1:
            destino = registrar(nome_d, regra["para"][0], trechos=onde_aparece(nome_d) or [primeiro])
        if origem is None or destino is None:
            descartes["relação com entidade ausente"] += 1
            continue

        tipo_o, tipo_d = entidades[origem]["type"], entidades[destino]["type"]
        if tipo_o in regra["de"] and tipo_d in regra["para"]:
            pass
        elif tipo_d in regra["de"] and tipo_o in regra["para"]:
            origem, destino = destino, origem
            descartes["relação corrigida (direção invertida)"] += 1
        else:
            descartes["relação com tipos incompatíveis"] += 1
            continue
        if origem == destino:
            descartes["relação de uma entidade com ela mesma"] += 1
            continue

        numero = trecho_valido(bruto.get("trecho"))
        if numero is None:
            em_ambos = set(onde_aparece(nome_o)) & set(onde_aparece(nome_d))
            candidatos = sorted(em_ambos) or onde_aparece(nome_o) or [primeiro]
            numero = candidatos[0]
        relacoes.add((origem, tipo, destino, ids_dos_trechos[numero]))
        for ident in (origem, destino):            # o trecho que sustenta o fato menciona as duas entidades
            entidades[ident]["chunk_ids"].add(ids_dos_trechos[numero])
    return entidades, relacoes


def unir(total: dict, novas: dict) -> None:
    """Junta entidades de lotes diferentes do mesmo artigo (mesmo id)."""
    for ident, ent in novas.items():
        atual = total.setdefault(ident, {"id": ident, "name": ent["name"], "type": ent["type"],
                                         "aliases": set(), "description": "", "chunk_ids": set()})
        atual["aliases"] |= ent["aliases"]
        atual["chunk_ids"] |= ent["chunk_ids"]
        if ent["description"] and not atual["description"]:
            atual["description"] = ent["description"]


# ---------------------------------------------------------------- chamadas ao Groq

class Ritmo:
    """Segura as chamadas para ficar abaixo dos limites por minuto (requisições e tokens)."""

    def __init__(self, requisicoes: int = REQUISICOES_POR_MINUTO, tokens: int = TOKENS_POR_MINUTO):
        self.requisicoes, self.tokens = requisicoes, tokens
        self.janela: deque[tuple[float, int]] = deque()

    def esperar(self, estimativa: int) -> None:
        while True:
            agora = time.time()
            while self.janela and agora - self.janela[0][0] > 60:
                self.janela.popleft()
            usados = sum(t for _, t in self.janela)
            if not self.janela or (len(self.janela) < self.requisicoes and usados + estimativa <= self.tokens):
                return
            time.sleep(max(0.5, 60 - (agora - self.janela[0][0]) + 0.2))

    def registrar(self, tokens: int) -> None:
        self.janela.append((time.time(), tokens))


def opcoes_do_modelo(modelo: str, esforco: str | None) -> dict:
    opcoes = {"response_format": {"type": "json_object"}, "max_tokens": MAX_TOKENS_RESPOSTA}
    if esforco:
        opcoes["reasoning_effort"] = esforco
    elif modelo.startswith("openai/gpt-oss"):
        opcoes["reasoning_effort"] = "low"   # menos tokens gastos "pensando"
    return opcoes


def chamar_modelo(modelo: str, mensagens: list[dict], opcoes: dict, ritmo: Ritmo) -> tuple[dict, int]:
    """Chama o Groq com retentativas limitadas e diagnóstico de HTTP 429."""
    estimativa = sum(len(m["content"]) for m in mensagens) // 3 + MAX_TOKENS_RESPOSTA // 2
    opcoes = dict(opcoes)
    esperas_429 = tentativas = 0
    MAX_RETENTATIVAS_429 = 3
    MAX_ESPERA_429 = 90  # segundos, para não ficar preso em esperas diárias

    while True:
        tentativas += 1
        ritmo.esperar(estimativa)
        try:
            resposta, _ = conversar(modelo, mensagens, **opcoes)
        except ErroGroq as erro:
            if erro.status == 429:
                esperas_429 += 1
                cabecalhos = {str(k).lower(): v for k, v in (erro.cabecalhos or {}).items()}
                try:
                    espera = float(cabecalhos.get("retry-after") or 5)
                except (TypeError, ValueError):
                    espera = 5.0
                print(f"\n[Groq 429] Limite atingido. Tentativa {esperas_429}/{MAX_RETENTATIVAS_429}. "
                      f"Espera solicitada: {espera:.1f}s.", flush=True)
                print(f"[Groq] Detalhes: {erro}", flush=True)
                if esperas_429 >= MAX_RETENTATIVAS_429:
                    raise RuntimeError("Groq retornou HTTP 429 repetidamente. Verifique a cota da conta.") from erro
                if not (0 <= espera <= MAX_ESPERA_429):
                    raise RuntimeError(f"Groq solicitou espera de {espera:.1f}s. "
                                       "Execução interrompida; cache das chamadas concluídas preservado.") from erro
                print(f"[Groq] Nova tentativa em {espera + 0.5:.1f}s.", flush=True)
                time.sleep(espera + 0.5)
                continue
            if erro.status == 400:
                retirou = [c for c in ("reasoning_effort", "response_format")
                           if c in opcoes and c in str(erro).lower()]
                for chave in retirou:
                    opcoes.pop(chave)
                if retirou:
                    continue
            if erro.status >= 500 and tentativas < 4:
                print(f"\n[Groq] Erro HTTP {erro.status}. Nova tentativa em 5s.", flush=True)
                time.sleep(5)
                continue
            raise
        usados = int((resposta.get("usage") or {}).get("total_tokens") or estimativa)
        ritmo.registrar(usados)
        conteudo = resposta["choices"][0]["message"].get("content") or ""
        try:
            return extrair_json(conteudo), usados
        except ValueError:
            if tentativas >= 4:
                raise RuntimeError("o modelo não devolveu JSON válido depois de 4 tentativas")


def chave_do_cache(modelo: str, titulo: str, lote: list[dict], esforco: str | None) -> str:
    base = json.dumps({"v": VERSAO_PROMPT, "m": modelo, "e": esforco, "t": titulo,
                       "c": [(c["id"], c["text"]) for c in lote]}, ensure_ascii=False)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------- artigos

def processar_artigo(artigo: str, args, dominio: dict, prompt: str, ritmo: Ritmo, estat: Counter) -> dict:
    dados = json.loads((CHUNKS / f"{artigo}.json").read_text(encoding="utf-8"))
    titulo = dados["documento"]["title"]
    selecionados = dados["chunks"][: args.max_chunks] if args.max_chunks else dados["chunks"]
    entidades: dict[str, dict] = {}
    relacoes: set[tuple] = set()
    descartes: Counter = Counter()

    for lote in montar_lotes(selecionados, args.lote):
        arquivo = CACHE / f"{chave_do_cache(args.modelo, titulo, lote, args.esforco)}.json"
        if arquivo.exists():
            resposta = json.loads(arquivo.read_text(encoding="utf-8"))
            estat["chamadas_do_cache"] += 1
        else:
            mensagens = [{"role": "system", "content": prompt},
                         {"role": "user", "content": mensagem_do_lote(titulo, lote)}]
            resposta, usados = chamar_modelo(args.modelo, mensagens, opcoes_do_modelo(args.modelo, args.esforco), ritmo)
            arquivo.parent.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(json.dumps(resposta, ensure_ascii=False), encoding="utf-8")
            estat["chamadas_ao_groq"] += 1
            estat["tokens"] += usados
        novas, rels = processar_resposta(resposta, lote, dominio, descartes)
        unir(entidades, novas)
        relacoes |= rels

    saida = {
        "documento": dados["documento"],
        "chunks": dados["chunks"],   # todos os trechos entram no banco, mesmo os que não passaram pela extração
        "entidades": [
            {"id": e["id"], "name": e["name"], "type": e["type"], "aliases": sorted(e["aliases"]),
             "description": e["description"], "chunk_ids": sorted(e["chunk_ids"])}
            for e in sorted(entidades.values(), key=lambda e: e["id"])
        ],
        "relacoes": [{"origem": o, "destino": d, "tipo": t, "chunk_id": c} for o, t, d, c in sorted(relacoes)],
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"{artigo}.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    estat["entidades"] += len(saida["entidades"])
    estat["relacoes"] += len(saida["relacoes"])
    estat.update({f"descarte: {k}": v for k, v in descartes.items()})
    return {"trechos": len(selecionados), "entidades": len(saida["entidades"]),
            "relacoes": len(saida["relacoes"]), "descartes": dict(descartes)}


def escolher_artigos(args) -> list[str]:
    if args.artigos:
        return args.artigos
    if args.todos:
        return [m["id"] for m in json.loads(MANIFESTO.read_text(encoding="utf-8"))]
    perguntas = json.loads(PERGUNTAS.read_text(encoding="utf-8"))["perguntas"]
    return sorted({a for p in perguntas for a in p["artigos_origem"]})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extrai entidades e relações dos trechos com o Groq.")
    parser.add_argument("--artigos", nargs="+", help="ids dos artigos (padrão: os das perguntas de avaliação)")
    parser.add_argument("--todos", action="store_true", help="todos os artigos do manifesto")
    parser.add_argument("--max-chunks", type=int, default=20, help="primeiros N trechos de cada artigo (0 = todos)")
    parser.add_argument("--lote", type=int, default=TRECHOS_POR_LOTE, help="trechos por chamada")
    parser.add_argument("--modelo", default=None, help=f"modelo do Groq (padrão: GROQ_MODEL do .env ou {MODELO_PADRAO})")
    parser.add_argument("--esforco", default=None, help="reasoning_effort (low, medium, high), se o modelo aceitar")
    parser.add_argument("--dry-run", action="store_true", help="só conta as chamadas, sem usar a cota")
    args = parser.parse_args(argv)

    carregar_env()
    args.modelo = args.modelo or os.getenv("GROQ_MODEL") or MODELO_PADRAO
    dominio = carregar_dominio()
    prompt = construir_prompt(dominio)
    artigos = escolher_artigos(args)

    faltando = [a for a in artigos if not (CHUNKS / f"{a}.json").exists()]
    if faltando:
        print(f"Sem arquivo de trechos para: {', '.join(faltando)}. Rode antes: python src/pipeline/chunking.py")
        return 1

    if args.dry_run:
        chamadas = tokens = 0
        for artigo in artigos:
            dados = json.loads((CHUNKS / f"{artigo}.json").read_text(encoding="utf-8"))
            selecionados = dados["chunks"][: args.max_chunks] if args.max_chunks else dados["chunks"]
            for lote in montar_lotes(selecionados, args.lote):
                if (CACHE / f"{chave_do_cache(args.modelo, dados['documento']['title'], lote, args.esforco)}.json").exists():
                    continue
                chamadas += 1
                tokens += (len(prompt) + len(mensagem_do_lote("x" * 20, lote))) // 3 + 700
        minutos = max(chamadas / REQUISICOES_POR_MINUTO, tokens / TOKENS_POR_MINUTO)
        print(f"{len(artigos)} artigos, modelo {args.modelo}: {chamadas} chamadas novas, "
              f"~{tokens:,} tokens, ~{minutos:.0f} min no ritmo permitido (estimativa grosseira).".replace(",", "."))
        return 0

    ritmo, estat, falhas = Ritmo(), Counter(), []
    inicio = time.time()
    for i, artigo in enumerate(artigos, start=1):
        print(f"[{i}/{len(artigos)}] {artigo} ... ", end="", flush=True)
        try:
            r = processar_artigo(artigo, args, dominio, prompt, ritmo, estat)
        except (ErroGroq, RuntimeError) as erro:
            print("ERRO")
            falhas.append((artigo, str(erro)))
            continue
        print(f"{r['trechos']} trechos, {r['entidades']} entidades, {r['relacoes']} relações")

    print(f"\n{len(artigos) - len(falhas)} de {len(artigos)} artigos em {SAIDA} ({(time.time() - inicio) / 60:.1f} min)")
    for chave, valor in sorted(estat.items()):
        print(f"  {chave}: {valor}")
    if falhas:
        print("\nArtigos com erro (rode de novo: o que já foi feito vem do cache):")
        for artigo, motivo in falhas:
            print(f"  - {artigo}: {motivo}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
