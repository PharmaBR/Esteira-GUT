# Esteira GUT

Uma fila pessoal de tarefas ordenada pela matriz GUT (Gravidade × Urgência × Tendência), com uma
única tarefa em execução por vez. Funciona no celular e no computador pelo navegador e pode ser
instalada na tela inicial.

## Duas versões, lado a lado

Cada pessoa tem duas esteiras, em abas:

- **Clássica** — fiel à ideia original. Três notas de 1 a 5 (**G**ravidade, **U**rgência,
  **T**endência), multiplicadas (máx. 125). A maior nota fica no topo; empates, na ordem de
  chegada. Só uma tarefa em execução por vez.
- **Aprimorada** — a mesma matriz, com as correções da auditoria metodológica: urgência
  calculada pelo prazo, nota dividida pelo esforço, crises na frente, desempate, bônus por tempo
  de espera, estados "pausada" e "bloqueada", triagem na entrada, teto de tarefas abertas e
  revisão semanal.

O porquê de cada regra, com o código, o teste e a referência científica de cada uma, está em
[`docs/auditoria.md`](docs/auditoria.md).

A fila é privada: cada pessoa entra com sua conta e só enxerga as próprias esteiras.

## Rodar no seu computador

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=1
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra <http://127.0.0.1:8000>. Novas contas são criadas em `/admin/` (não há cadastro aberto).

## Testes

```sh
pytest
ruff check . && ruff format --check .
```

## Publicar

A imagem (`Dockerfile`) aplica as migrações ao iniciar e serve a aplicação com gunicorn na porta 8000.
A rota `/saude/` responde `ok` para o health check.

| Variável | Para quê |
| --- | --- |
| `DJANGO_SECRET_KEY` | Obrigatória. `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | Domínio público, sem `https://` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origem completa, com `https://` |
| `DATABASE_URL` | `postgres://usuario:senha@host:5432/banco` |

**EasyPanel:** crie um serviço Postgres e um serviço App apontando para este repositório (build por
Dockerfile), preencha as variáveis acima, exponha a porta 8000 e aponte o domínio. Depois do
primeiro deploy, crie seu usuário pelo console do serviço: `python manage.py createsuperuser`.

**Docker Compose:** `cp .env.example .env`, preencha, e `docker compose up -d --build`.

## Organização

```
esteira/
  domain/     regras em Python puro (sem Django)
  boards/     models, views, templates e arquivos estáticos
  tests/      domain/ (regras) e boards/ (aplicação)
```

As duas versões compartilham tudo, menos a política: `ClassicGUT` e `EnhancedGUT` em
`esteira/domain/scoring.py`, escolhidas por `Board.mode`.

Convenções do projeto: [`CLAUDE.md`](CLAUDE.md).
