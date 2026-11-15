# Planilha de classificação manual

Gerada por `python -m src.avaliacao.comparar`, a partir das respostas em [data/avaliacao/resultados/respostas.json](../data/avaliacao/resultados/respostas.json). Para cada pergunta e modo, compare a resposta do sistema com a resposta esperada e escreva correta, incompleta ou alucinada.

As classes ficam em [data/avaliacao/classificacao.json](../data/avaliacao/classificacao.json), no formato `{"P01": {"vetorial": "correta", "graphrag": "incompleta"}}`. As perguntas `sem_resposta` já entram nesse arquivo pela regra: recusa correta vira correta, e qualquer outra resposta vira alucinada. Rodar o executor de novo regenera esta planilha, mas não apaga o arquivo de classificação.

## P01 (um_salto)

Pergunta: Quem criou a linguagem de programação Python?

Resposta esperada: Guido van Rossum.

### P01 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P01 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

## P02 (um_salto)

Pergunta: Em qual organização a linguagem Java foi desenvolvida?

Resposta esperada: Na Sun Microsystems, a partir de 1991.

### P02 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P02 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

## P03 (um_salto)

Pergunta: Quem desenvolveu o núcleo Linux?

Resposta esperada: O programador finlandês Linus Torvalds.

### P03 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P03 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

## P04 (um_salto)

Pergunta: Que prêmio Niklaus Wirth recebeu em 1984?

Resposta esperada: O Prêmio Turing, pelo desenvolvimento de uma sequência de linguagens de programação, incluindo o Pascal.

### P04 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P04 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

## P05 (um_salto)

Pergunta: Em qual organização Brian Kernighan trabalhou?

Resposta esperada: No Bell Labs, onde contribuiu com o desenvolvimento do Unix.

### P05 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P05 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

## P06 (multi_hop)

Pergunta: Que prêmio recebeu o criador da linguagem Lisp?

Resposta esperada: John McCarthy, criador do Lisp, recebeu o Prêmio Turing (1972, segundo o artigo).

### P06 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

### P06 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

## P07 (multi_hop)

Pergunta: Além do C, o C++ foi influenciado por outra linguagem de programação. Que prêmio receberam os criadores dessa linguagem?

Resposta esperada: A linguagem é o Simula (Simula 67), criada por Kristen Nygaard e Ole-Johan Dahl, que receberam o Prêmio Turing de 2001.

### P07 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/3)

Caminho completo: não (0/5)

Classificação: ____

### P07 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/3)

Caminho completo: não (1/5)

Classificação: ____

## P08 (multi_hop)

Pergunta: Que prêmio recebeu quem criou a linguagem que deu origem ao C?

Resposta esperada: O C derivou da linguagem B, criada por Ken Thompson, que recebeu o Prêmio Turing em 1983 (junto com Dennis Ritchie).

### P08 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/3)

Caminho completo: não (0/3)

Classificação: ____

### P08 graphrag

Resposta do sistema:

> A linguagem que deu origem ao C foi a B, criada por Ken Thompson [C1][F1][F7][F8]. Ele recebeu o Prêmio Turing da ACM em 1983 [C1][F6]. Também recebeu a Medalha IEEE Richard W. Hamming em 1990 e a Medalha Nacional de Tecnologia e Inovação em 1999 [C3][F6].

Evidência recuperada: não (2/3)

Caminho completo: sim

Classificação: ____

## P09 (multi_hop)

Pergunta: Qual pessoa que trabalhou no CERN recebeu o Prêmio Turing?

Resposta esperada: Tim Berners-Lee, que recebeu o Prêmio Turing de 2016 pela criação da World Wide Web.

### P09 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

### P09 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

## P10 (multi_hop)

Pergunta: Em qual organização trabalhava um dos inventores do Smalltalk quando se envolveu no projeto da linguagem?

Resposta esperada: Na Xerox PARC, onde Alan Kay era pesquisador desde 1971.

### P10 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

### P10 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

## P11 (multi_hop)

Pergunta: Quais pessoas que trabalharam no Bell Labs receberam o Prêmio Turing?

Resposta esperada: Dennis Ritchie e Ken Thompson, que receberam o Prêmio Turing em 1983. Brian Kernighan e Bjarne Stroustrup também trabalharam no Bell Labs, mas o dataset não diz que receberam o prêmio.

### P11 vetorial

Resposta do sistema:

> **Dennis Ritchie** e **Ken Thompson** trabalharam no Bell Labs e receberam o Prêmio Turing da ACM em 1983 [F1]. Ritchie começou no Bell Labs Computing Science Research Center em 1967 [F2], e os dois trabalharam juntos no sistema operacional Multics nos Bell Labs durante a década de 1960 [F3].

Evidência recuperada: não (2/3)

Caminho completo: não (0/4)

Classificação: ____

### P11 graphrag

Resposta do sistema:

> Dennis Ritchie e Ken Thompson trabalharam no Bell Labs e receberam o Prêmio Turing [C1][C2][C4]. Eles receberam o prêmio da ACM em 1983 [F1] e trabalharam juntos no Bell Labs, inclusive no Multics e no Unix [F3][F6]. Bjarne Stroustrup também trabalhou no Bell Labs, mas o contexto não diz que ele recebeu o Prêmio Turing [C3][F7].

Evidência recuperada: sim

Caminho completo: sim

Classificação: ____

## P12 (multi_hop)

Pergunta: A linguagem Python tem parte da sintaxe derivada de outra linguagem. Em qual organização essa outra linguagem foi criada?

Resposta esperada: A linguagem é o C, criado em 1972 por Dennis Ritchie no Bell Labs (AT&T).

### P12 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/2)

Caminho completo: não (0/2)

Classificação: ____

### P12 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/2)

Caminho completo: não (1/2)

Classificação: ____

## P13 (sem_resposta)

Pergunta: Quem criou a linguagem de programação Rust?

Resposta esperada: O sistema deve dizer que não encontrou a informação no dataset (nenhum artigo trata de Rust).

### P13 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

### P13 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

## P14 (sem_resposta)

Pergunta: Que prêmio Margaret Hamilton recebeu?

Resposta esperada: O sistema deve dizer que não encontrou a informação no dataset (Margaret Hamilton não aparece nos artigos).

### P14 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

### P14 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

## P15 (sem_resposta)

Pergunta: Em qual organização foi desenvolvida a linguagem Kotlin?

Resposta esperada: O sistema deve dizer que não encontrou a informação no dataset (nenhum artigo trata de Kotlin).

### P15 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

### P15 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: n/a

Caminho completo: n/a

Classificação: ____

