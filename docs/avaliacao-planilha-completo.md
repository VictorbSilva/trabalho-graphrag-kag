# Planilha de classificação manual

Gerada por `python -m src.avaliacao.comparar`, a partir das respostas em [data/avaliacao/resultados/completo/respostas.json](../data/avaliacao/resultados/completo/respostas.json). Para cada pergunta e modo, compare a resposta do sistema com a resposta esperada e escreva correta, incompleta ou alucinada.

As classes ficam em [data/avaliacao/resultados/completo/classificacao.json](../data/avaliacao/resultados/completo/classificacao.json), no formato `{"P01": {"vetorial": "correta", "graphrag": "incompleta"}}`. As perguntas `sem_resposta` já entram nesse arquivo pela regra: recusa correta vira correta, e qualquer outra resposta vira alucinada. Rodar o executor de novo regenera esta planilha, mas não apaga o arquivo de classificação.

## P01 (um_salto)

Pergunta: Quem criou a linguagem de programação Python?

Resposta esperada: Guido van Rossum.

### P01 vetorial

Resposta do sistema:

> Python foi lançada por Guido van Rossum em 1991 [F2]. Guido publicou o código, nomeado versão 0.9.0, no grupo de discussão alt.sources [F1].

Evidência recuperada: não (0/1)

Caminho completo: não (0/1)

Classificação: ____

### P01 graphrag

Resposta do sistema:

> Guido van Rossum criou a linguagem Python [C1][C2][F2]. Ele concebeu Python no final de 1989 no Instituto de Pesquisa Nacional para Matemática e Ciência da Computação (CWI), nos Países Baixos [F6].

Evidência recuperada: sim

Caminho completo: não (0/1)

Classificação: ____

## P02 (um_salto)

Pergunta: Em qual organização a linguagem Java foi desenvolvida?

Resposta esperada: Na Sun Microsystems, a partir de 1991.

### P02 vetorial

Resposta do sistema:

> Java foi desenvolvida na Sun Microsystems, a partir de 1991, no Green Project [F1][F3]. Em 2010, a Oracle Corporation concluiu a aquisição da Sun e passou a ser responsável pela continuidade comercial da tecnologia [F3].

Evidência recuperada: sim

Caminho completo: não (0/1)

Classificação: ____

### P02 graphrag

Resposta do sistema:

> Java foi desenvolvida na Sun Microsystems [C1][C3][F1]. O desenvolvimento começou em 1991 na Sun Microsystems, com o Green Project [F1], e a linguagem foi desenvolvida por uma equipe liderada por James Gosling [F3].

Evidência recuperada: sim

Caminho completo: sim

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

> O Linux foi criado por Linus Torvalds [C1]. O desenvolvimento também contou com a colaboração de grupos de entusiastas e de grandes empresas, como IBM, Red Hat e Google [F4].

Evidência recuperada: não (0/1)

Caminho completo: sim

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

> Niklaus Wirth recebeu o Prêmio Turing em 1984 [C1][F6]. O prêmio foi concedido pela Association for Computing Machinery (ACM) pelo desenvolvimento de sua sequência de linguagens de programação [F7].

Evidência recuperada: sim

Caminho completo: sim

Classificação: ____

## P05 (um_salto)

Pergunta: Em qual organização Brian Kernighan trabalhou?

Resposta esperada: No Bell Labs, onde contribuiu com o desenvolvimento do Unix.

### P05 vetorial

Resposta do sistema:

> Brian Kernighan trabalhou na Bell Labs [F1]. Lá, ele contribuiu com o desenvolvimento do Unix junto de Ken Thompson e Dennis Ritchie [F1].

Evidência recuperada: sim

Caminho completo: não (0/1)

Classificação: ____

### P05 graphrag

Resposta do sistema:

> Brian Kernighan trabalhou na Bell Labs [C1][F1]. Essa relação aparece nos caminhos do grafo com a aresta TRABALHOU_EM [C1] e é confirmada no texto, que diz que ele trabalhou na Bell Labs [F1].

Evidência recuperada: sim

Caminho completo: sim

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

> O criador da linguagem Lisp, John McCarthy, recebeu o Prêmio Turing [C1][C4] e a Medalha Nacional de Ciências dos Estados Unidos [C2][C3]. O contexto indica que ele recebeu o Prêmio Turing de 1972 e a medalha de 1991 [F6].

Evidência recuperada: não (1/2)

Caminho completo: não (1/2)

Classificação: ____

## P07 (multi_hop)

Pergunta: Além do C, o C++ foi influenciado por outra linguagem de programação. Que prêmio receberam os criadores dessa linguagem?

Resposta esperada: A linguagem é o Simula (Simula 67), criada por Kristen Nygaard e Ole-Johan Dahl, que receberam o Prêmio Turing de 2001.

### P07 vetorial

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/3)

Caminho completo: não (0/5)

Classificação: ____

### P07 graphrag

Resposta do sistema:

> Não encontrei essa informação no dataset.

Evidência recuperada: não (0/3)

Caminho completo: não (0/5)

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

> Não encontrei essa informação no dataset.

Evidência recuperada: não (1/3)

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

Evidência recuperada: não (1/2)

Caminho completo: não (1/2)

Classificação: ____

## P10 (multi_hop)

Pergunta: Em qual organização trabalhava um dos inventores do Smalltalk quando se envolveu no projeto da linguagem?

Resposta esperada: Na Xerox PARC, onde Alan Kay era pesquisador desde 1971.

### P10 vetorial

Resposta do sistema:

> O contexto não informa explicitamente para qual organização os inventores trabalhavam. Ted Kaehler integrava a equipe original do Learning Research Group [F2]. A Xerox aparece apenas depois do Smalltalk-80, quando criou a ParcPlace para cuidar do desenvolvimento da linguagem [F5].

Evidência recuperada: não (0/2)

Caminho completo: não (0/2)

Classificação: ____

### P10 graphrag

Resposta do sistema:

> Alan Kay trabalhava na Xerox PARC quando se envolveu com o projeto da linguagem Smalltalk, pois passou a ser pesquisador da empresa em 1971 e se envolveu com o projeto em 1971 e 1972 [F6]. O grafo também indica que o Smalltalk foi desenvolvido em Xerox PARC [C3].

Evidência recuperada: não (1/2)

Caminho completo: não (0/2)

Classificação: ____

## P11 (multi_hop)

Pergunta: Quais pessoas que trabalharam no Bell Labs receberam o Prêmio Turing?

Resposta esperada: Dennis Ritchie e Ken Thompson, que receberam o Prêmio Turing em 1983. Brian Kernighan e Bjarne Stroustrup também trabalharam no Bell Labs, mas o dataset não diz que receberam o prêmio.

### P11 vetorial

Resposta do sistema:

> Alfred Aho e Jeffrey Ullman dividiram o Prêmio Turing de 2020 pelo trabalho com compiladores, iniciado quando trabalharam juntos no Bell Labs entre 1967 e 1969 [F1]. O contexto também informa que pesquisadores do Bell Labs receberam o Prêmio Turing em cinco edições [F4][F5], mas não nomeia os outros premiados.

Evidência recuperada: não (0/3)

Caminho completo: não (0/4)

Classificação: ____

### P11 graphrag

Resposta do sistema:

> Alfred V. Aho e Ken Thompson trabalharam no Bell Labs e receberam o Prêmio Turing [C1][C2][C5]. Aho dividiu o prêmio de 2020 com Jeffrey Ullman pelo trabalho com compiladores [F1]. Alan Turing e Brian Kernighan aparecem no grafo como trabalhadores do Bell Labs, mas não como recipientes do prêmio [C3][C4].

Evidência recuperada: não (0/3)

Caminho completo: não (2/4)

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

> Python tem parte da sintaxe derivada do C [F4]. A linguagem C foi desenvolvida na Nokia [C1]. O [F6] também associa o local de desenvolvimento da linguagem C à unidade da Nokia em Murray Hill.

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

