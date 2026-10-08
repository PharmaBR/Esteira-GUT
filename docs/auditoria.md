# Auditoria metodológica da Esteira GUT

Este documento explica por que a esteira **aprimorada** se comporta de forma diferente da
**clássica**. Cada regra nasce de um achado da auditoria, aponta para o código que a implementa,
para o teste que a protege e para a fonte que a sustenta.

A esteira clássica continua disponível, intacta, na aba "Clássica". As duas usam o mesmo código;
só troca a política de priorização (`Board.mode`).

## Resumo

| Regra | Achado na clássica | O que a aprimorada faz |
| --- | --- | --- |
| R1 | Urgência é um palpite e nunca muda | Com prazo, a urgência é calculada a cada dia |
| R2 | 4×4×4 = 64 passa na frente de 5×5×2 = 50 | Gravidade 5 com urgência 5 fura a fila |
| R3 | Uma tarefa de dias trava dez de minutos | A nota é dividida pelo esforço |
| R4 | Empate sem prazo fica na ordem de chegada | Desempate por prazo, depois por idade |
| R5 | Nota baixa nunca chega ao topo | Cada semana de espera soma pontos |
| R6 | Tarefa que depende de terceiros prende a vaga | Estado "bloqueada", com motivo |
| R7 | Tudo o que entra acaba sendo feito | Triagem: só entra o que é importante e seu |
| R8 | A fila cresce sem limite | Teto de tarefas abertas; descarte que pode ser desfeito |
| R9 | Emergência é atendida por fora | Pausa explícita, com motivo e contagem |
| R10 | Ninguém confere se as notas acertaram | Esforço real e veredito na conclusão; revisão semanal |
| R11 | O 3 vem marcado e a ajuda manda usá-lo na dúvida | Escalas descritas no próprio campo, sem valor pré-selecionado |

## O que a esteira clássica já acerta

**F1. Três critérios e uma nota.** Separar as preocupações e ordená-las por gravidade, urgência
e tendência vem da análise de situação de Kepner e Tregoe [1]. "GUT" é o nome que a literatura
brasileira de gestão deu a esses três critérios, com escalas de 1 a 5.

**F2. Uma tarefa por vez.** Alternar entre tarefas custa tempo a cada troca, e o custo cresce com
a complexidade da tarefa [10]. Parte da atenção fica presa na tarefa anterior e piora o
desempenho na seguinte [11]. Limitar o trabalho em andamento é o princípio central do
Kanban [13].

**F3. Decidir a prioridade no cadastro, não na hora de executar.** Planos do tipo "quando X,
farei Y" aumentam a chance de a meta ser cumprida [23]. Fazer um plano para uma pendência
elimina a interferência que ela causa em outras atividades [22].

> **Correção.** Em uma conversa anterior justifiquei este ponto com "fadiga de decisão". A
> evidência para esse efeito é fraca: uma replicação pré-registrada, feita em vários laboratórios, encontrou
> efeito próximo de zero (d = 0,04; IC 95% de −0,07 a 0,15) [24]. A justificativa correta é a
> do parágrafo acima.

## Regras da esteira aprimorada

Código das políticas: [`esteira/domain/scoring.py`](../esteira/domain/scoring.py). Código dos
estados e travas: [`esteira/domain/rules.py`](../esteira/domain/rules.py). Os testes ficam em
[`esteira/tests/domain/`](../esteira/tests/domain/) e
[`esteira/tests/boards/test_enhanced_board.py`](../esteira/tests/boards/test_enhanced_board.py),
com o número da regra nos comentários.

### R1. Urgência calculada pelo prazo

**Achado.** Na clássica a urgência é digitada uma vez e fica parada, embora o tempo passe. Além
disso, urgência e tendência se sobrepõem: o que piora rápido já tende a ser urgente, e o efeito
é contado duas vezes.

**Regra.** Se a tarefa tem prazo, a urgência é calculada a partir dos dias que faltam, toda vez
que a fila é ordenada. Sem prazo, vale a urgência escolhida à mão.

| Dias até o prazo | Urgência |
| --- | --- |
| hoje ou atrasada | 5 |
| 1 a 2 | 4 |
| 3 a 7 | 3 |
| 8 a 14 | 2 |
| 15 ou mais | 1 |

**Fonte.** Ordenar pelo prazo mais próximo é a resposta clássica da teoria de sequenciamento
quando o objetivo é não estourar prazos: minimiza o maior atraso [8]. Aqui o prazo alimenta a
urgência em vez de substituir a ordem, porque gravidade e tendência continuam contando.

**Código e teste.** `urgency_from_deadline`, `EnhancedGUT.priority` · bloco R1 de
`test_enhanced_policy.py`.

### R2. Crise fura a fila

**Achado.** As notas de 1 a 5 são ordinais: dizem que 5 é mais que 4, não que é "25% a mais".
Multiplicar escalas ordinais produz um número que parece medida e não é [2]. O mesmo problema é
conhecido no número de prioridade de risco da FMEA, também um produto de três notas: poucos
valores distintos, combinações diferentes com o mesmo resultado e valores que não se comparam
de forma linear [3][4].
Matrizes de risco ordinais têm baixa resolução e podem ordenar riscos de forma errada [5].

**Regra.** Tarefa com gravidade 5 e urgência 5 vai para o topo, qualquer que seja o produto.
Entre crises, vale a prioridade normal.

**Limite.** A regra corrige a inversão mais cara, não o problema de fundo. Uma sequência
ininterrupta de crises adia todo o resto, e isso é intencional.

**Código e teste.** `EnhancedGUT.priority` (campo `crisis`) · bloco R2 de
`test_enhanced_policy.py`.

### R3. A nota é dividida pelo esforço

**Achado.** A clássica ignora quanto tempo a tarefa leva. Uma tarefa de dias com nota 125 segura
uma de dez minutos com nota 100.

**Regra.** Prioridade = G × U × T ÷ peso do esforço. O esforço é estimado em cinco tamanhos:

| Tamanho | Até | Peso |
| --- | --- | --- |
| XS | 15 minutos | 1 |
| S | 1 hora | 2 |
| M | meio período | 3 |
| L | um dia | 5 |
| XL | mais de um dia | 8 |

**Fonte.** Com uma única máquina, ordenar as tarefas pela razão entre peso e duração minimiza a
soma ponderada dos tempos de conclusão (regra de Smith) [6]. É o mesmo raciocínio do "custo do
atraso dividido pela duração" em desenvolvimento de produto [7].

**Limite.** A regra de Smith é ótima quando o peso é uma medida real e a duração é conhecida. A
nota GUT é ordinal e o esforço é uma estimativa em faixas, então aqui a divisão é uma
heurística, não um ótimo demonstrado.

**Código e teste.** `Effort`, `EnhancedGUT.priority` · bloco R3 de `test_enhanced_policy.py`.

### R4. Desempate por prazo, depois por idade

**Achado.** As 125 combinações de notas produzem apenas 30 valores distintos (há um teste que
conta). Empate é a regra, não a exceção. O mesmo acontece com o número de prioridade de risco
[3][4]. A clássica já desempata pelo prazo mais próximo. Quando nenhuma das tarefas empatadas
tem prazo, fica a ordem de chegada, e a nota nunca muda com o tempo.

> **Correção.** A primeira versão desta auditoria dizia que a clássica não tinha desempate. Eu
> ainda não tinha visto o texto de ajuda do original, que diz: "Em empate, vem antes a de prazo
> mais próximo." A clássica foi corrigida para fazer exatamente isso, e este achado foi reescrito.

**Regra.** A aprimorada mantém o desempate da clássica e o completa. Entre prioridades iguais,
vence o prazo mais próximo. Tarefa com prazo vence tarefa sem prazo. Persistindo o empate,
vence a mais antiga. Como a urgência é recalculada pelo prazo (R1) e a espera soma pontos (R5),
os empates também ficam mais raros.

**Fonte.** Prazo mais próximo primeiro [8].

**Código e teste.** `sort_key` em `EnhancedGUT.priority` · bloco R4 de `test_enhanced_policy.py`.
O desempate da clássica está em `ClassicGUT.priority` e em `test_classic_policy.py`.

### R5. Esperar aumenta a prioridade

**Achado.** Uma tarefa de nota baixa pode ficar para sempre atrás das que chegam. Só anda quando
vira crise.

**Regra.** Cada semana completa na esteira soma 2 pontos à prioridade.

**Fonte.** É o "envelhecimento" que sistemas operacionais usam contra a inanição em
escalonamento por prioridade: aumentar aos poucos a prioridade de quem espera há muito
tempo [9].

**Garantia.** A prioridade sem bônus tem teto (125) e o bônus não tem. Logo, toda tarefa acaba
passando à frente de qualquer outra que não seja crise. No pior caso possível (nota 1, esforço
XL, contra tarefas ideais chegando sem parar), isso leva 50 semanas; o teste
`test_nothing_starves_...` verifica.

**Código e teste.** `aging_points_per_week` em `EnhancedGUT` · bloco R5 de
`test_enhanced_policy.py`.

### R6. Estado "bloqueada"

**Achado.** Se a tarefa no topo depende de outra pessoa, ela ocupa a única vaga sem que nada
possa ser feito. A auditoria original também apontou a falta de dependências entre tarefas; o
bloqueio com motivo cobre esse caso sem criar um grafo de dependências.

**Regra.** Uma tarefa na fila, em execução ou pausada pode ser bloqueada, com motivo
obrigatório. Ela sai da fila e libera a vaga. Desbloqueada, volta para a fila.

**Fonte.** Tornar visível o trabalho impedido, em vez de deixá-lo ocupando capacidade, é prática
do Kanban [13].

**Código e teste.** `TRANSITIONS`, `ensure_reason`, `Task.block` · `test_enhanced_workflow.py`
e bloco R6 de `test_enhanced_board.py`.

### R7. Triagem na entrada

**Achado.** A matriz GUT ordena, mas não filtra. Tudo o que entra na fila acaba sendo feito, em
algum momento.

**Regra.** Para entrar, a tarefa precisa de duas confirmações: "é importante para um objetivo
meu" e "só eu posso fazer". Sem a primeira, a orientação é descartar. Sem a segunda, delegar.

**Fonte.** As pessoas tendem a escolher tarefas urgentes de menor valor em vez de tarefas
importantes de maior valor, só por causa da sensação de urgência [14]. A distinção entre urgente
e importante foi popularizada por Covey [15]. A frase original é de um discurso de Eisenhower
em 1954, em que ele a atribui a "um ex-reitor" [16].

**Código e teste.** `triage` · `test_enhanced_workflow.py` e bloco R7 de
`test_enhanced_board.py`.

### R8. Teto de tarefas abertas e descarte

**Achado.** Uma fila sem limite cresce até deixar de ser consultada.

**Regra.** A esteira aceita no máximo 20 tarefas abertas (na fila, em execução, pausadas ou
bloqueadas). Cheia, recusa a nova tarefa e mantém o que foi digitado. Para abrir espaço,
conclua ou descarte. A tarefa descartada sai da fila e vai para a lista "Descartadas", de onde
pode ser restaurada. Por isso o descarte acontece na hora, sem pergunta de confirmação.

**Fonte.** Pela lei de Little, o tempo médio que um item passa no sistema é o número médio de
itens dividido pela taxa de saída [17]. Com a mesma capacidade de trabalho, mais tarefas abertas
significam espera proporcionalmente maior. Limitar o trabalho em andamento é a aplicação
prática [13].

**Código e teste.** `ensure_capacity`, `Board.ensure_room`, `Task.discard`, `Task.restore` · bloco R8 de
`test_enhanced_board.py`.

### R9. Pausa explícita, com motivo e contagem

**Achado.** Quando surge uma emergência, ela é atendida por fora e o sistema deixa de refletir
a realidade.

**Regra.** Na aprimorada não existe "devolver à fila" em silêncio. Para sair da vaga sem
concluir é preciso pausar (interrupção) ou bloquear (dependência), dizendo o motivo. Cada pausa
soma uma interrupção à tarefa, e o tempo trabalhado é acumulado entre as pausas.

**Fonte.** Trabalho interrompido é concluído com mais estresse, frustração e pressão de
tempo [12]. Trocar de tarefa custa tempo [10] e deixa resíduo de atenção [11]. Contar as
interrupções é o primeiro passo para reduzi-las.

**Código e teste.** `Task.pause`, `Task.resume` · bloco R9 de `test_enhanced_board.py`.

### R10. Retroalimentação

**Achado.** Nada verifica se as notas e as estimativas estavam certas.

**Regra.** Ao concluir, a aprimorada pergunta quanto a tarefa levou de fato (já sugerindo o
tamanho medido pelo relógio) e se a prioridade estava certa. A página "Revisão semanal" resume
acertos e erros de estimativa, os vereditos de prioridade, as interrupções, as tarefas paradas
há duas semanas ou mais e as bloqueadas.

**Fonte.** As pessoas subestimam de forma sistemática o tempo das próprias tarefas, porque
planejam imaginando o cenário futuro em vez de consultar a experiência passada [21]. Confrontar
a estimativa com o histórico é o corretivo.

**Código e teste.** `estimate_accuracy`, `CompletionForm`, view `review` · bloco R10 de
`test_enhanced_board.py`.

### R11. Escalas descritas, sem valor padrão

**Achado.** A clássica traz o 3 já marcado, e a própria ajuda orienta: "Na dúvida, use 3 e
ajuste depois." As notas tendem a se acumular em 27. A ajuda descreve os níveis 5, 3 e 1 de
cada critério, mas a descrição fica fechada em um painel, longe do campo em que a nota é
escolhida.

**Regra.** O formulário da aprimorada não sugere nota. Cada um dos cinco níveis de cada escala
diz o que significa dentro do próprio campo, e as descrições de urgência coincidem com a tabela
de prazos da R1. As descrições são curtas de propósito: cada uma cabe inteira no campo fechado
em um celular.

**Fonte.** Estimativas ficam presas a um valor inicial, mesmo arbitrário (ancoragem) [19]. A
opção pré-selecionada tende a ser mantida: países em que a doação de órgãos é o padrão têm taxas
de consentimento muito maiores [20]. Ancorar cada nível de uma escala em descrições concretas
reduz a ambiguidade entre avaliadores [18].

**Código e teste.** `ANCHORS`, `EnhancedTaskForm` · `test_anchors.py`.

## Interface

O desenho das telas tem documento próprio: [`design.md`](../design.md). Ele vale para as duas
versões e foi feito para leitura fácil e pouca distração, com base em orientações de
acessibilidade cognitiva [25][26][27]. Em resumo:

- **Uma família de letras** feita para que nenhum caractere se confunda com outro. Nada em
  maiúsculas ou itálico. Texto em 17 px, com entrelinha folgada.
- **Papel creme e tinta quase preta**, sem fundo estampado. O vermelho é a única cor de
  destaque e marca só o que pede atenção agora: a tarefa em execução, crise, prazo vencido e
  erro. Ele sempre vem acompanhado de palavras.
- **Lista com fios no lugar de cartões**, tudo alinhado à esquerda, na mesma ordem em todas as
  telas.
- **Rótulo visível em todo campo** e palavras literais. Cada nota vem explicada em palavras
  ("Fazer já", "Nesta semana"), como na legenda do original.
- **Nada se move nem some sozinho.** Avisos de erro ficam até serem fechados. O formulário não
  muda de altura quando aparece um erro. O que pode ser desfeito não pede confirmação.

A clássica também recuperou o que o original tinha e a primeira reconstrução não mostrava: o
texto de ajuda, a legenda das quatro faixas de nota e o aviso de quando a primeira da fila
passa a ter nota maior que a tarefa em execução.

Continuam valendo as três correções de tela feitas desde o início: o campo de data tem rótulo
("Prazo"), o botão "Adicionar à fila" fica depois dos campos, e a esteira só aparece para quem
entrou com a própria conta.

Compromissos com hora marcada (aulas, reuniões) não competem por prioridade. Pertencem ao
calendário, e a ajuda da esteira diz isso.

## O que é escolha de projeto

Os números abaixo não vêm da literatura. São pontos de partida razoáveis, isolados como
parâmetros para serem ajustados quando houver dados de uso.

| Parâmetro | Valor | Onde |
| --- | --- | --- |
| Faixas de dias → urgência | 0, 2, 7, 14 | `DEADLINE_URGENCY` |
| Pesos de esforço | 1, 2, 3, 5, 8 | `Effort` |
| Bônus por semana de espera | 2 pontos | `EnhancedGUT.aging_points_per_week` |
| Esforço quando não informado | M | `EnhancedGUT.effort_when_unknown` |
| Teto de tarefas abertas | 20 | `Board.queue_limit` (editável no admin) |
| "Parada" na revisão | 2 semanas | `STALE_AFTER_WEEKS` |

## Limites das evidências

- As fontes sustentam os **princípios**, não esta implementação. Nenhum estudo testou a
  esteira aprimorada. A comparação honesta é usar as duas abas com tarefas reais e olhar a
  revisão semanal.
- Não consultei o texto integral de Kepner e Tregoe [1]. A correspondência entre os critérios
  do livro e a sigla GUT vem da literatura secundária brasileira, que diverge sobre datas.
- Os estudos de troca de tarefa e interrupção [10][11][12] são de laboratório ou de simulação de
  escritório. A direção do efeito é consistente; o tamanho no seu dia a dia pode ser outro.
- A regra de Smith [6] e a lei de Little [17] são resultados matemáticos, válidos sob as
  hipóteses de cada modelo.
- As orientações de interface [25][26][27] são guias de boas práticas escritos com pessoas
  autistas, disléxicas e com outras diferenças cognitivas. Não são ensaios controlados, e essas
  pessoas não formam um grupo com necessidades iguais. O desenho segue os pontos em que os três
  guias concordam. A letra escolhida foi criada para baixa visão: ela torna os caracteres mais
  distintos, mas não há prova de que melhore a leitura de pessoas disléxicas.

## Referências

Cada referência foi conferida em 8 de outubro de 2026 em catálogo de biblioteca, página da
editora ou do periódico, ou na lista de referências de um artigo que a cita. O DOI aparece
quando a fonte consultada o trazia.

1. Kepner, C. H., & Tregoe, B. B. (1965). *The rational manager: A systematic approach to
   problem solving and decision making*. New York: McGraw-Hill.
2. Stevens, S. S. (1946). On the theory of scales of measurement. *Science, 103*(2684), 677–680.
3. Bowles, J. B. (2004). An assessment of RPN prioritization in a failure modes effects and
   criticality analysis. *Journal of the IEST, 47*(1), 51–56.
4. Ciani, L., Guidi, G., & Patrizi, G. (2019). A critical comparison of alternative risk
   priority numbers in failure modes, effects, and criticality analysis. *IEEE Access, 7*,
   92398–92409. <https://doi.org/10.1109/ACCESS.2019.2928120>
5. Cox, L. A., Jr. (2008). What's wrong with risk matrices? *Risk Analysis, 28*(2), 497–512.
6. Smith, W. E. (1956). Various optimizers for single-stage production. *Naval Research
   Logistics Quarterly, 3*, 59–66.
7. Reinertsen, D. G. (2009). *The principles of product development flow*. Celeritas.
   ISBN 978-1-935401-00-1.
8. Jackson, J. R. (1955). *Scheduling a production line to minimize maximum tardiness*.
   Relatório técnico, University of California, Los Angeles.
9. Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). *Operating system concepts* (10ª ed.).
   Wiley. Capítulo de escalonamento de CPU, escalonamento por prioridade.
10. Rubinstein, J. S., Meyer, D. E., & Evans, J. E. (2001). Executive control of cognitive
    processes in task switching. *Journal of Experimental Psychology: Human Perception and
    Performance, 27*(4), 763–797. <https://doi.org/10.1037/0096-1523.27.4.763>
11. Leroy, S. (2009). Why is it so hard to do my work? The challenge of attention residue when
    switching between work tasks. *Organizational Behavior and Human Decision Processes,
    109*(2), 168–181.
12. Mark, G., Gudith, D., & Klocke, U. (2008). The cost of interrupted work: More speed and
    stress. *Proceedings of CHI 2008*, 107–110.
13. Anderson, D. J. (2010). *Kanban: Successful evolutionary change for your technology
    business*. Blue Hole Press. ISBN 978-0-9845214-0-1.
14. Zhu, M., Yang, Y., & Hsee, C. K. (2018). The mere urgency effect. *Journal of Consumer
    Research, 45*(3), 673–690. <https://doi.org/10.1093/jcr/ucy008>
15. Covey, S. R. (1989). *The 7 habits of highly effective people*. Free Press.
16. Eisenhower, D. D. (1954, 19 de agosto). *Address at the Second Assembly of the World
    Council of Churches, Evanston, Illinois*. The American Presidency Project.
    <https://www.presidency.ucsb.edu/node/232572>
17. Little, J. D. C. (1961). A proof for the queuing formula: L = λW. *Operations Research,
    9*(3), 383–387. <https://doi.org/10.1287/opre.9.3.383>
18. Smith, P. C., & Kendall, L. M. (1963). Retranslation of expectations: An approach to the
    construction of unambiguous anchors for rating scales. *Journal of Applied Psychology,
    47*(2), 149–155. <https://doi.org/10.1037/h0047060>
19. Tversky, A., & Kahneman, D. (1974). Judgment under uncertainty: Heuristics and biases.
    *Science, 185*, 1124–1131.
20. Johnson, E. J., & Goldstein, D. (2003). Do defaults save lives? *Science, 302*(5649),
    1338–1339.
21. Buehler, R., Griffin, D., & Ross, M. (1994). Exploring the "planning fallacy": Why people
    underestimate their task completion times. *Journal of Personality and Social Psychology,
    67*(3), 366–381.
22. Masicampo, E. J., & Baumeister, R. F. (2011). Consider it done! Plan making can eliminate
    the cognitive effects of unfulfilled goals. *Journal of Personality and Social Psychology,
    101*(4), 667–683. <https://doi.org/10.1037/a0024192>
23. Gollwitzer, P. M. (1999). Implementation intentions: Strong effects of simple plans.
    *American Psychologist, 54*, 493–503.
24. Hagger, M. S., Chatzisarantis, N. L. D., Alberts, H., et al. (2016). A multilab
    preregistered replication of the ego-depletion effect. *Perspectives on Psychological
    Science, 11*(4), 546–573. <https://doi.org/10.1177/1745691616652873>
25. W3C (2021). *Making content usable for people with cognitive and learning disabilities*.
    W3C Working Group Note. <https://www.w3.org/TR/coga-usable/>
26. Pun, K. (2016). *Dos and don'ts on designing for accessibility*. Accessibility in
    government, GOV.UK. <https://accessibility.blog.gov.uk/2016/09/02/dos-and-donts-on-designing-for-accessibility/>
27. Ako Aotearoa (2023). *Dyslexia-friendly style guide*.
    <https://ako.ac.nz/assets/Knowledge-centre/ALNACC-Resources/Dyslexia-resources/230907-Dyslexia-Friendly-Style-Guide.pdf>
