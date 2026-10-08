# Esteira GUT

Fila pessoal de tarefas priorizada pela matriz GUT. Django + htmx, um deploy, duas versões
(clássica e aprimorada) escolhidas pelo campo `Board.mode`.

## Regras do projeto

- **Toda requisição mostra status.** Qualquer elemento com `hx-get`/`hx-post`/… precisa de
  `hx-indicator` (apontando para algo com a classe `htmx-indicator`) e de `hx-disabled-elt`.
  A barra global e as mensagens de falha ficam em `static/boards/js/app.js`.
  `esteira/tests/boards/test_status_indicator.py` quebra o build se uma requisição for silenciosa.
- **Teste primeiro.** Regra nova começa por um teste em `esteira/tests/domain/`.
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
