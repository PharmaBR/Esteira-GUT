# Esteira GUT

Fila pessoal de tarefas priorizada pela matriz GUT. Django + htmx, um deploy, duas versões
(clássica e aprimorada) escolhidas pelo campo `Board.mode`.

## Regras do projeto

- **Toda requisição mostra status.** Qualquer elemento com `hx-get`/`hx-post`/… precisa de
  `hx-indicator` (apontando para algo com a classe `htmx-indicator`) e de `hx-disabled-elt`.
  A barra global e as mensagens de falha ficam em `static/boards/js/app.js`: a barra aparece na
  hora e fica pelo menos 300 ms; o giro dentro do controle só aparece depois de 150 ms; o controle
  é desabilitado na hora. `esteira/tests/boards/test_status_indicator.py` quebra o build se uma
  requisição for silenciosa.
- **Teste primeiro.** Regra nova começa por um teste em `esteira/tests/domain/`.
- **Regra da aprimorada tem número.** R1 a R11 em `docs/auditoria.md`; o mesmo número aparece nos
  comentários do código e dos testes. Regra nova ou alterada atualiza os três.
- **A clássica não muda.** Ela é a linha de base para comparação; melhorias vão na aprimorada.
  Só muda para ficar mais fiel ao original, com teste em `tests/boards/test_original_fidelity.py`.
- **O visual segue `design.md`.** Cores e fontes só por token (`static/boards/css/tokens.css`);
  nada de maiúsculas, itálico, cartão, sombra ou animação fora dos indicadores; todo campo tem
  rótulo visível; vermelho só para "precisa de você agora", sempre com palavras. Para mudar o
  sistema, altere `design.md` e `tokens.css` juntos. `tests/boards/test_design_system.py` confere.
- **Toda ação responde onde a pessoa está olhando.** Mensagem de erro curta, na linha reservada
  do campo (o formulário não pula); ação recusada leva o foco até a mensagem; nada de validação
  nativa do navegador. `tests/boards/test_feedback.py` confere.
- **Domínio em Python puro.** `esteira/domain/` não importa Django. As regras de negócio moram lá;
  os models (`esteira/boards/models.py`) pedem permissão ao domínio antes de mudar de estado.
- **Active Record, sem repositórios.** Models do Django chamam o domínio direto.
- **Sem JSON, sem API.** O servidor responde HTML; toda ação devolve o bloco `#board` inteiro.
- **Dono em toda consulta.** Views buscam com `owner=request.user` / `board__owner=request.user`.
- **Sem código inline.** A CSP proíbe `<script>`/`<style>` inline e origens externas.
- Interface e documentação em português; identificadores e comentários de código em inglês.

## Comandos

```sh
export DJANGO_DEBUG=1
python manage.py migrate && python manage.py runserver
pytest                      # suíte inteira (menos de 2 s)
ruff check . && ruff format --check .
```
