# PA6 — Relatório de Validação do Pipeline GraphRAG/KAG

## 1. Objetivo

Documentar a execução e a validação do pipeline de extração de entidades e relações, resolução de entidades, curadoria semântica e integração com o banco de grafos Neo4j.

## 2. Processamento do dataset

Foram processados 31 dos 32 artigos previstos (96,9%) sobre história da computação.

A extração utilizou os provedores Groq e Google Gemini, preservando o formato JSON definido para o projeto.

O artigo sobre o Instituto de Tecnologia de Massachusetts (MIT) permaneceu incompleto devido ao limite diário de requisições da API Gemini.

## 3. Resultados da extração e avaliação

- Artigos concluídos: 31 de 32.
- Relações extraídas, incluindo ocorrências repetidas: 964.
- Relações distintas identificadas na avaliação: 745.
- Relações esperadas encontradas: 21 de 24 (87,5%).
- Perguntas com caminhos completos: 10 de 12.

As três relações esperadas não encontradas foram:

- Kristen Nygaard RECEBEU Prêmio Turing.
- Ole-Johan Dahl RECEBEU Prêmio Turing.
- C DESENVOLVIDA_EM Bell Labs.

Essas ausências foram registradas sem adicionar relações artificiais ao grafo.

## 4. Resolução de entidades e curadoria

A etapa de resolução e curadoria foi executada sobre os 31 artigos.

Resultados da curadoria:

- Relações aceitas: 47.
- Relações rejeitadas: 10.
- Relações pendentes de revisão: 907.
- Conflitos de status após unificação: 0.

A exportação curada é uma prévia destinada à auditoria. O banco utilizado na demonstração contém as relações extraídas e validadas estruturalmente, não apenas as relações aprovadas manualmente.

As relações pendentes não devem ser descritas como semanticamente validadas.

## 5. Integração com o Neo4j

A ingestão foi executada localmente com:

python -m src.banco.ingestor

Resultados confirmados no banco:

- Documentos: 31.
- Trechos: 1.440.
- Entidades: 1.298.
- Relações entre entidades: 745.

Todos os arquivos processados foram aceitos pelo ingestor.

A demonstração com dados reais permite recuperar o caminho:

C++ -> C -> Dennis Ritchie -> Prêmio Turing

O grafo mantém referências aos trechos utilizados como evidência.

## 6. Análise do grafo

As rotinas de PageRank e detecção de comunidades foram executadas com:

docker compose run --rm neo4j-gds

Resultados:

- Nós com PageRank atualizado: 1.298.
- Iterações do PageRank: 90.
- Convergência do PageRank: confirmada.
- Comunidades detectadas: 719.
- Modularidade: aproximadamente 0,8424.
- Nós com comunidade atribuída: 1.298.

## 7. Testes automatizados

Com o Neo4j local em execução, foi executado:

python -m pytest -q

Resultado final:

- Testes aprovados: 515.
- Falhas: 0.
- Testes ignorados: 0.
- Avisos: 1.
- Tempo de execução: 122,91 segundos.

O aviso está relacionado à depreciação de CallSpec2 no plugin anyio/pytest e não representa falha nos testes.

## 8. Limitações

- Um dos 32 artigos previstos não foi concluído.
- A revisão semântica permanece parcial.
- A extração automática pode produzir entidades repetidas e relações que exigem revisão humana.
- A avaliação encontrou 21 das 24 relações esperadas.
- A aprovação da suíte de testes não substitui a revisão semântica das relações pendentes.

## 9. Conclusão

O pipeline demonstrou capacidade de processar artigos da Wikipédia, extrair entidades e relações, produzir JSONs compatíveis com o esquema do projeto e integrar os resultados ao Neo4j.

A ingestão de 31 artigos, a execução dos algoritmos de análise do grafo e a aprovação de 515 testes automatizados demonstram o funcionamento técnico da solução.

O principal trabalho futuro é ampliar a curadoria semântica, resolver equivalências adicionais entre entidades e concluir o processamento do artigo restante.
