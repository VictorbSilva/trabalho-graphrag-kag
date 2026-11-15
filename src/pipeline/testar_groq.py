"""Testa a chave do Groq e mede o limite de requisições (critério da issue #5).

Uso, na raiz do repositório, com GROQ_API_KEY preenchida no .env:

    python src/pipeline/testar_groq.py --listar
    python src/pipeline/testar_groq.py --modelo NOME_DO_MODELO
    python src/pipeline/testar_groq.py --modelo NOME_DO_MODELO --rajada 20

--listar   mostra os modelos que a sua conta enxerga
--modelo   faz uma chamada mínima e mostra tempo, tokens usados e os limites da conta
--rajada N manda N chamadas seguidas para ver se o limite por minuto estoura (gasta pouca cota)

No fim imprime um bloco pronto para colar num comentário da issue.
"""

import argparse
import sys
import time
from datetime import datetime

from groq_cliente import ErroGroq, conversar, limites_dos_cabecalhos, listar_modelos

PEDIDO = [{"role": "user", "content": "Responda apenas com a palavra: ok"}]


def chamada_minima(modelo: str) -> tuple[float, dict, dict]:
    inicio = time.perf_counter()
    dados, cabecalhos = conversar(modelo, PEDIDO, max_tokens=8)
    return time.perf_counter() - inicio, dados.get("usage", {}), cabecalhos


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa a chave e os limites do Groq.")
    parser.add_argument("--listar", action="store_true", help="lista os modelos disponíveis")
    parser.add_argument("--modelo", help="modelo a testar")
    parser.add_argument("--rajada", type=int, default=0, help="chamadas seguidas extras (máx. 60)")
    args = parser.parse_args()

    try:
        if args.listar:
            modelos = listar_modelos()
            print(f"{len(modelos)} modelos na sua conta:")
            for m in modelos:
                contexto = m.get("context_window")
                print(f"  {m['id']}" + (f"   (contexto: {contexto})" if contexto else ""))
            if not args.modelo:
                print("\nEscolha um e rode: python src/pipeline/testar_groq.py --modelo NOME")
                return 0

        if not args.modelo:
            parser.error("informe --listar ou --modelo")

        tempo, uso, cabecalhos = chamada_minima(args.modelo)
        limites = limites_dos_cabecalhos(cabecalhos)
        print(f"Chamada ok em {tempo:.2f}s | tokens usados: {uso}")
        print("Limites informados pela API:")
        for nome, valor in limites.items():
            print(f"  {nome}: {valor}")
        if not limites:
            print("  (a API não devolveu cabeçalhos de limite: anote os do painel do console)")

        resultados = {"ok": 0, "429": 0, "outros": 0}
        primeiro_429 = None
        for _ in range(min(max(args.rajada, 0), 60)):
            try:
                _, _, cabecalhos = chamada_minima(args.modelo)
                resultados["ok"] += 1
            except ErroGroq as erro:
                if erro.status == 429:
                    resultados["429"] += 1
                    primeiro_429 = primeiro_429 or limites_dos_cabecalhos(erro.cabecalhos)
                else:
                    resultados["outros"] += 1
                    print(f"  erro inesperado: {erro}")
        if args.rajada:
            print(f"\nRajada de {args.rajada}: {resultados}")
            if primeiro_429:
                print(f"No primeiro 429: {primeiro_429}")
            limites = limites_dos_cabecalhos(cabecalhos) or limites

        print("\n--- cole na issue #5 ---")
        print(f"Limite do Groq testado em {datetime.now():%d/%m/%Y %H:%M}, modelo `{args.modelo}`:")
        for nome, valor in limites.items():
            print(f"- {nome}: {valor}")
        if args.rajada:
            print(f"- rajada de {args.rajada} chamadas seguidas: {resultados['ok']} ok, {resultados['429']} com 429")
        print("(os limites diários também estão na página de limites do console do Groq)")
        return 0
    except ErroGroq as erro:
        print(f"Erro do Groq: {erro}")
        if erro.status in (401, 403):
            print("A chave foi recusada: confira GROQ_API_KEY no .env (sem aspas e sem espaços).")
        return 1
    except RuntimeError as erro:
        print(erro)
        return 1


if __name__ == "__main__":
    sys.exit(main())
