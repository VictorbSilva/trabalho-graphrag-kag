import os
import json
from pathlib import Path

def carregar_configuracoes():
    # Parâmetros recomendados para GraphRAG
    return {
        "chunk_size": 1000,    # Quantidade de caracteres por pedaço
        "chunk_overlap": 200,  # Sobreposição para não perder contexto entre os cortes
        "dir_entrada": Path("data/bruto"),
        "dir_saida": Path("data/processado/chunks")
    }

def dividir_em_chunks(texto, chunk_size, chunk_overlap):
    """
    Divide o texto em pedaços menores com base em caracteres, 
    garantindo o overlap entre eles.
    """
    if not texto:
        return []
    
    chunks = []
    inicio = 0
    tamanho_texto = len(texto)

    while inicio < tamanho_texto:
        fim = inicio + chunk_size
        chunk = texto[inicio:fim]
        chunks.append(chunk)
        # Avança o ponteiro considerando o overlap
        inicio += chunk_size - chunk_overlap

    return chunks

def processar_chunking():
    config = carregar_configuracoes()
    
    # Cria a pasta de saída caso não exista
    config["dir_saida"].mkdir(parents=True, exist_ok=True)
    
    if not config["dir_entrada"].exists():
        print(f"[Erro] A pasta de entrada '{config['dir_entrada']}' não foi encontrada.")
        print("Certifique-se de que os artigos brutos estão no local correto.")
        return

    arquivos_txt = list(config["dir_entrada"].glob("*.txt"))
    
    if not arquivos_txt:
        print(f"[Aviso] Nenhum arquivo .txt encontrado em '{config['dir_entrada']}'.")
        return

    print(f"Iniciando o chunking de {len(arquivos_txt)} arquivos...")
    
    total_chunks_gerados = 0
    manifesto_chunks = []

    for arquivo_path in arquivos_txt:
        nome_arquivo = arquivo_path.name
        texto_completo = arquivo_path.read_text(encoding="utf-8")
        
        # Realiza o fatiamento
        pedacos = dividir_em_chunks(
            texto_completo, 
            config["chunk_size"], 
            config["chunk_overlap"]
        )
        
        print(f" -> {nome_arquivo}: gerou {len(pedacos)} chunks.")

        # Salva os pedaços individualmente
        for i, conteudo_chunk in enumerate(pedacos):
            chunk_id = f"{arquivo_path.stem}_chunk_{i:03d}"
            caminho_chunk = config["dir_saida"] / f"{chunk_id}.txt"
            
            # Salva o arquivo de texto do chunk
            caminho_chunk.write_text(conteudo_chunk, encoding="utf-8")
            
            # Guarda metadados para rastreabilidade
            manifesto_chunks.append({
                "chunk_id": chunk_id,
                "origem": nome_arquivo,
                "indice": i,
                "caminho_arquivo": str(caminho_chunk)
            })
            total_chunks_gerados += 1

    # Salva o manifesto geral dos chunks gerados
    caminho_manifesto = config["dir_saida"].parent / "manifesto_chunks.json"
    caminho_manifesto.write_text(
        json.dumps(manifesto_chunks, ensure_ascii=False, indent=4), 
        encoding="utf-8"
    )

    print("\n--- Chunking Concluído com Sucesso! ---")
    print(f"Total de chunks criados: {total_chunks_gerados}")
    print(f"Manifesto salvo em: {caminho_manifesto}")

if __name__ == "__main__":
    processar_chunking()