# Recuperação

## Arquitetura da recuperação

A recuperação recebe uma pergunta em linguagem natural e devolve a resposta junto com as evidências que a sustentam. O ponto de entrada é a função `responder`, que funciona em dois modos. No modo vetorial, o sistema usa apenas os trechos de documento mais parecidos com a pergunta. No modo GraphRAG, ele parte desses mesmos trechos, chega às entidades que eles citam e percorre o grafo de conhecimento a partir delas.

Os dois modos seguem a mesma sequência. Primeiro vem a busca vetorial nos trechos. No modo GraphRAG, segue a expansão multi-hop pelo grafo. Depois o sistema monta as fontes, gera o texto com um LLM a partir de um contexto numerado, confere as citações e calcula o nível de confiança. Por fim, o resultado é validado contra o contrato da resposta, definido com Pydantic em `src/contrato.py`. A validação roda em toda resposta, inclusive nas recusas e nas falhas do LLM, e rejeita qualquer campo que o contrato não preveja. Assim, a API e a interface recebem sempre o mesmo formato, com a resposta, a confiança, os caminhos, o subgrafo, as fontes e os avisos.

Todas as consultas da recuperação ao Neo4j rodam em transação de leitura. Responder a uma pergunta nunca altera o grafo.

## Busca vetorial

Os trechos dos documentos e as perguntas são convertidos em vetores pelo modelo paraphrase-multilingual-MiniLM-L12-v2, que gera embeddings de 384 dimensões. Os vetores são normalizados. O mesmo módulo do código gera o vetor dos trechos na ingestão e o da pergunta na consulta, o que garante que a busca compare vetores produzidos da mesma forma. Ao carregar o modelo, o sistema confere se a dimensão gerada é a que o índice vetorial espera e interrompe a execução se não for.

A busca consulta o índice vetorial do Neo4j e devolve os cinco trechos mais parecidos com a pergunta, cada um com o título e a URL do documento de origem. O índice compara os vetores pelo cosseno, mas devolve o score na faixa de 0 a 1, calculado como (1 + cosseno) / 2. Nessa escala, um trecho sem relação nenhuma com a pergunta tem score 0,5, e não 0. O cálculo da confiança desfaz essa conversão.

O modelo lê no máximo 128 tokens de cada texto e ignora o restante. Por isso os documentos são divididos em trechos de até 450 caracteres, cortados entre frases. Só uma frase que sozinha passa do limite é quebrada, e mesmo assim entre palavras. Com essa regra, 17 dos 1633 trechos do dataset do pipeline (1%) ainda passam de 128 tokens. Nenhuma das 22 evidências da avaliação está na parte cortada desses trechos.

A busca foi conferida com a semente, um conjunto pequeno de trechos, entidades e relações anotados à mão. No teste `tests/recuperacao/test_busca_semente.py`, 12 de 12 perguntas tiveram um trecho certo entre os três primeiros resultados. Algumas perguntas têm mais de um trecho certo, e o gabarito do teste aceita todos eles. As posições podem ser reproduzidas com `python -m src.avaliacao.posicoes_semente`, que imprime a posição do primeiro trecho certo de cada pergunta.

## Expansão multi-hop

No modo GraphRAG, os trechos da busca são a porta de entrada no grafo. Cada trecho está ligado às entidades que menciona. A expansão parte dessas entidades e anda de 1 a 3 saltos, usando só as relações do domínio, lidas do schema do projeto: CRIOU, TRABALHOU_EM, DESENVOLVIDA_EM, INFLUENCIADA_POR e RECEBEU. As ligações estruturais, como a que liga um trecho ao seu documento, ficam fora do percurso.

A consulta ao grafo ordena os caminhos pelo score do trecho de origem e, depois, pelos mais curtos. Caminhos com as mesmas arestas aparecem uma vez só, e fica o de maior score. Em seguida, cada caminho é escrito como uma frase, por exemplo "C++ foi influenciada por C; Dennis Ritchie criou C", e essa frase é comparada com a pergunta pelo mesmo modelo de embeddings da busca. O sistema também identifica, pelo começo da pergunta, o tipo de entidade pedido. "Quem" pede uma pessoa, e "Que prêmio" pede um prêmio.

A ordem final põe primeiro os caminhos que têm uma ponta do tipo pedido, sem descartar os outros. Depois ordena pela similaridade com a pergunta, pelo score do trecho de origem, pela média do PageRank dos nós e, por último, pelo tamanho do caminho. O PageRank é calculado antes, com a biblioteca GDS do Neo4j. A resposta usa os cinco primeiros caminhos dessa ordem.

As fontes da resposta são os trechos da busca, seguidos dos trechos que sustentam as relações dos caminhos e que a busca não trouxe. Esses últimos entram sem score. O total fica limitado a oito fontes.

## Text-to-Cypher

No modo GraphRAG, além da expansão, o sistema pede ao LLM uma consulta Cypher para a pergunta. A expansão parte só dos trechos que a busca encontrou. A Cypher anda direto pelas relações que a pergunta pede.

Antes de gerar a consulta, o sistema procura os nomes citados na pergunta no índice fulltext `entity_search` do Neo4j. Cada palavra da pergunta vira uma busca, e ficam as cinco entidades de maior score para cada uma. O prompt traz o schema do domínio, lido de `neo4j/dominio.json`, com os rótulos e as relações na direção em que estão no grafo. Traz também os identificadores reais das entidades encontradas e três exemplos de pergunta com a Cypher correspondente. As instruções pedem que a consulta devolva caminhos, para que o resultado tenha o mesmo formato dos caminhos da expansão.

A consulta gerada não roda direto. Quando ela não tem LIMIT no final, o sistema acrescenta LIMIT 25. Em seguida, ela passa pelo EXPLAIN do Neo4j, que analisa a consulta sem executá-la e devolve o erro quando ela é inválida. Só então a consulta roda, sempre em transação de leitura. Se a validação ou a execução falhar, o LLM recebe a consulta anterior com a mensagem de erro do Neo4j e tem mais uma tentativa.

A proteção contra escrita fica com o banco, e não com um filtro de palavras sobre o texto da consulta. Numa transação de leitura, o Neo4j recusa CREATE, MERGE, SET e DELETE, e essa recusa vale para qualquer consulta, seja qual for o texto. O EXPLAIN não serve como proteção, porque aceita um CREATE mesmo em transação de leitura, já que não executa nada. Quem barra a escrita é a execução. Um teste confere que uma consulta com CREATE é recusada e que nada é gravado no grafo.

O Text-to-Cypher tem limites de tempo próprios. Cada chamada ao LLM tem 10 segundos. O conjunto tem um orçamento de 20 segundos, e a segunda tentativa não acontece se a primeira já passou dele. A execução da consulta no banco tem 5 segundos.

Os caminhos da Cypher se juntam aos da expansão. Caminhos com as mesmas arestas aparecem uma vez só, e fica o da expansão, que tem o score do trecho de origem. A união passa pela mesma ordenação descrita na seção anterior, com o tipo de resposta pedido, a similaridade com a pergunta, o score, o PageRank e o tamanho, e é cortada nos cinco primeiros caminhos. Assim, os caminhos da Cypher disputam lugar com os da expansão em vez de se somarem a eles no contexto.

Uma falha do Text-to-Cypher não interrompe a resposta. Ela vira um aviso no campo `avisos`, e a resposta segue com a busca e a expansão. O campo `cypher` da resposta traz a consulta executada, ou fica nulo quando houve falha, e o resultado do Text-to-Cypher entra no cálculo da confiança.

## Grounding e procedência

O LLM não recebe o grafo nem os documentos inteiros. Ele recebe um contexto numerado. Cada caminho ocupa uma linha identificada como C1, C2 e assim por diante, com as entidades e as relações na direção em que estão no grafo. Cada trecho ocupa uma linha identificada como F1, F2, com o título do documento. As instruções pedem que o modelo responda só com base nesse contexto, em até três frases, e que cite cada afirmação com os identificadores entre colchetes. Se o contexto não tiver a resposta, o modelo deve escrever exatamente "Não encontrei essa informação no dataset." A chamada usa a API da Abacus RouteLLM com temperatura 0.

Depois da geração, o sistema extrai as citações do texto e confere se cada uma existe entre os caminhos e as fontes enviados. Uma citação inexistente não é apagada nem corrigida. Ela vira um aviso no campo `avisos` da resposta, para que o leitor saiba que aquela afirmação aponta para algo que o sistema não forneceu.

A procedência vai até o texto original. Cada caminho guarda os identificadores dos trechos que sustentam suas relações, e cada fonte traz o trecho, o título do documento e a URL. Uma afirmação citada pode ser seguida da resposta ao caminho, do caminho ao trecho e do trecho ao artigo de onde ele veio.

Quando a busca e a expansão não trazem nada, o LLM nem é chamado. O sistema recusa com a mesma mensagem e registra um aviso de que nenhum trecho ou caminho foi encontrado. Se a chamada ao LLM falhar, a resposta diz que não foi possível gerá-la e remete às fontes recuperadas.

## Nível de confiança

O nível de confiança sai só de sinais observáveis da recuperação. Nenhum LLM avalia a própria resposta. A regra completa está em `docs/confianca.md`, e aqui fica o raciocínio por trás dela.

O primeiro sinal é o melhor score da busca vetorial. Como o índice devolve (1 + cosseno) / 2, a regra volta para o cosseno, com cosseno = max(0, 2 × score - 1). Sem essa volta, qualquer pergunta, mesmo fora do domínio, partiria de 0,5. No modo GraphRAG, o segundo sinal é a maior similaridade entre a pergunta e a frase de um caminho. Ter caminho não diz muito, porque a expansão sempre encontra algum a partir dos trechos da busca. Um caminho parecido com a pergunta diz mais.

No modo GraphRAG, o valor é a média desses dois sinais, multiplicada pela fração de caminhos que têm trecho de origem em todas as relações. No modo vetorial, sem caminhos, o valor é 0,7 vezes o cosseno. Sem caminho no grafo não há como conferir relações, então essa resposta não passa de 0,7. O valor é zero quando não há contexto e quando o LLM falha ou recusa a pergunta, porque nesses casos não existe resposta a qual atribuir confiança. A partir de 0,7 o nível é alto, de 0,4 até menos de 0,7 é médio, e abaixo de 0,4 é baixo. O campo `criterio` registra os números usados no cálculo, e a interface o mostra ao lado do nível.

Quando o Text-to-Cypher falha, o valor perde 0,1, e o campo `criterio` registra o desconto. Quando a Cypher roda sem erro, e no modo vetorial, em que ela não é usada, o valor não muda.

## Exemplo completo

O exemplo a seguir foi gerado em 15 de novembro de 2026, com a semente carregada no Neo4j e o PageRank calculado. O texto da resposta e a consulta Cypher vieram do modelo claude-opus-5-5-fast, pela Abacus RouteLLM, com temperatura 0. O JSON completo da resposta está em `docs/artigo/exemplo-resposta-real.json`, e as partes reproduzidas aqui foram copiadas dele sem edição. A pergunta, no modo GraphRAG, foi:

> Que prêmio recebeu quem criou a linguagem que influenciou o C++?

Responder exige três saltos: do C++ à linguagem que o influenciou, dela a quem a criou e dessa pessoa ao prêmio.

A busca vetorial trouxe cinco trechos, o melhor com score 0,82. A expansão devolveu cinco caminhos. O Text-to-Cypher gerou e executou esta consulta:

```cypher
MATCH p = (:Tecnologia {id: 'tecnologia:c_mais_mais'})-[:INFLUENCIADA_POR]->(:Tecnologia)<-[:CRIOU]-(:Pessoa)-[:RECEBEU]->(:Premio) RETURN p LIMIT 25
```

A consulta parte do nó do C++, pelo id `tecnologia:c_mais_mais`, e faz os três saltos da pergunta: a linguagem que influenciou o C++, quem a criou e os prêmios dessa pessoa. Ela devolveu dois caminhos, os dois por Dennis Ritchie, um até o Prêmio Turing e outro até a Medalha Nacional de Tecnologia e Inovação. A expansão já tinha encontrado os dois, e na união ficaram as cópias da expansão. Neste exemplo, portanto, a Cypher não acrescentou caminho novo, e os cinco caminhos da resposta são os mesmos da expansão.

Como a pergunta começa por "Que prêmio", os caminhos que terminam num prêmio vêm primeiro, e os cinco terminam num prêmio. A resposta citou dois deles, mostrados aqui como o LLM os recebeu no contexto:

```
[C1] C++ -[INFLUENCIADA_POR]-> C <-[CRIOU]- Dennis Ritchie -[RECEBEU]-> Prêmio Turing
[C4] C++ -[INFLUENCIADA_POR]-> C <-[CRIOU]- Dennis Ritchie -[RECEBEU]-> Medalha Nacional de Tecnologia e Inovação
```

O caminho C1 diz que o C++ foi influenciado pelo C, que Dennis Ritchie criou o C e que Dennis Ritchie recebeu o Prêmio Turing. O C4 faz o mesmo percurso até a Medalha Nacional de Tecnologia e Inovação. Os outros três caminhos passam por Ken Thompson, pelas linguagens B e BCPL e pelo Bell Labs, e não foram citados.

A resposta gerada foi:

> O C++ foi influenciado pela linguagem C, criada por Dennis Ritchie no AT&T Bell Labs [C1][F5]. Ritchie recebeu o **Prêmio Turing** da ACM em 1983, junto com Ken Thompson [C1][F7]. Também recebeu a Medalha IEEE Richard W. Hamming em 1990 e a Medalha Nacional de Tecnologia e Inovação em 1999 [C4][F7].

As duas fontes citadas foram estas.

F5, do documento "C (linguagem de programação)", `https://pt.wikipedia.org/wiki/C_(linguagem_de_programa%C3%A7%C3%A3o)`, score 0.7378809452056885:

> C é uma linguagem de programação compilada de propósito geral, estruturada, imperativa, procedural, padronizada pela Organização Internacional para Padronização (ISO), criada em 1972 por Dennis Ritchie na empresa AT&T Bell Labs para desenvolvimento do sistema operacional Unix (originalmente escrito em Assembly).

F7, do documento "Dennis Ritchie", `https://pt.wikipedia.org/wiki/Dennis_Ritchie`, sem score:

> Dennis Ritchie e Ken Thompson receberam o Prêmio Turing da Association for Computing Machinery (ACM) em 1983, a Medalha IEEE Richard W. Hamming do Institute of Electrical and Electronics Engineers (IEEE) em 1990 e a Medalha Nacional de Tecnologia e Inovação, concedida pelo presidente Bill Clinton em 1999.

O trecho F7, que sustenta o prêmio, não estava entre os cinco da busca. Ele entrou nas fontes porque sustenta a relação RECEBEU do caminho C1, e por isso não tem score. No modo vetorial, o contexto teria só os cinco trechos da busca, e nenhum deles fala de prêmio.

A confiança da resposta saiu assim:

```json
{
  "valor": 0.59,
  "nivel": "media",
  "criterio": "score 0.82 (cosseno 0.64), similaridade do caminho 0.54, 5 de 5 caminhos com trecho de origem"
}
```

O valor segue a regra: (0,5 × 0,64 + 0,5 × 0,54) × 5/5 = 0,59, nível médio. Como a Cypher rodou sem erro, não houve desconto. O campo `avisos` veio vazio, porque o Text-to-Cypher não falhou e todas as citações existem no contexto.

## Limitações e trabalhos futuros

O próprio exemplo mostra o limite da checagem de citações. Ela confere se o identificador existe, não se o caminho ou o trecho citado sustenta a afirmação. Na última frase da resposta, a Medalha IEEE Richard W. Hamming aparece citada com [C4][F7]. O trecho F7 menciona essa medalha, mas o caminho C4 trata só da Medalha Nacional de Tecnologia e Inovação. A citação passou porque os dois identificadores existem. Como trabalho futuro, a checagem deve verificar se o trecho citado sustenta a afirmação, e não só se o identificador existe.

A expansão também traz caminhos que não respondem à pergunta. No exemplo, três dos cinco passam por Ken Thompson e chegam ao Prêmio Turing por outro lado. Eles ocupam espaço no contexto, e cabe ao LLM descartá-los. A detecção do tipo pedido olha só o começo da pergunta e uma lista fixa de palavras. Uma pergunta formulada de outro jeito fica sem tipo, e a ordem dos caminhos passa a depender só da similaridade e dos scores.

Na busca, 17 dos 1633 trechos do dataset do pipeline (1%) têm o final ignorado pelo modelo de embeddings. Esse número não vale para a semente da demo. Os trechos da semente são parágrafos inteiros anotados à mão e não passaram pelo chunking. Três dos 12 passam do limite de 128 tokens do modelo: `c#2` (147 tokens), `c_mais_mais#1` (247) e `dennis_ritchie#4` (140). Os três aparecem nas fontes do exemplo, como F1, F4 e F8. No teste da semente, a pergunta "Quem criou a linguagem C?" acerta no limite, com o trecho certo em 3º lugar.

A consulta do Text-to-Cypher depende do LLM. O schema, os identificadores e os exemplos do prompt orientam a geração, e a validação impede que uma consulta inválida chegue a rodar, mas nada garante que a consulta gerada seja a que a pergunta pede. Uma consulta válida que anda pelas relações erradas devolve caminhos sem relação com a pergunta, sem erro e sem aviso. Os caminhos que só a Cypher encontra também não partem de nenhum trecho da busca. Eles chegam à ordenação sem trecho de origem e com score 0, e o score, que nos caminhos da expansão indica o quanto o trecho de partida se parece com a pergunta, não conta a favor deles. As relações desses caminhos continuam ligadas aos trechos que as sustentam, então a procedência até o documento se mantém.
