# Esteira GUT

Uma fila pessoal de tarefas ordenada pela matriz GUT (Gravidade × Urgência × Tendência), com uma
única tarefa em execução por vez. Funciona no celular e no computador pelo navegador e pode ser
instalada na tela inicial.

## Duas versões, lado a lado

Cada pessoa tem duas esteiras, em abas:

- **Clássica** — fiel à ideia original. Três notas de 1 a 5 (**G**ravidade, **U**rgência,
  **T**endência), multiplicadas (máx. 125). A maior nota fica no topo; empates, pelo prazo mais
  próximo. Cada nota cai em uma faixa: fazer já (75 ou mais), nesta semana (40 a 74), agendar
  (20 a 39) e quando sobrar tempo. Só uma tarefa em execução por vez.
- **Aprimorada** — a mesma matriz, com as correções da auditoria metodológica: urgência
  calculada pelo prazo, nota dividida pelo esforço, crises na frente, desempate, bônus por tempo
  de espera, estados "pausada" e "bloqueada", triagem na entrada, teto de tarefas abertas e
  revisão semanal.

O porquê de cada regra, com o código, o teste e a referência científica de cada uma, está em
[`docs/auditoria.md`](docs/auditoria.md).

A fila é privada: cada pessoa entra com sua conta e só enxerga as próprias esteiras.

## Visual

A interface foi desenhada para ser calma e fácil de ler, com atenção a quem é neurodivergente: uma
família tipográfica de alta legibilidade, papel creme, fios em vez de caixas, um único vermelho
para o que precisa de você agora, rótulos sempre visíveis e nada que se mexa ou suma sozinho. As
regras e os motivos estão em [`design.md`](design.md).

As fontes Atkinson Hyperlegible Next e Mono (Braille Institute, licença SIL OFL 1.1) são servidas
pela própria aplicação; as licenças estão em `esteira/boards/static/boards/fonts/`.

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

**VPS vazio (Docker Manager da Hostinger, Portainer ou `docker compose`):** use
[`deploy/docker-compose.vps.yml`](deploy/docker-compose.vps.yml). Ele sobe Caddy (HTTPS automático),
a aplicação e o Postgres, e constrói a imagem direto do repositório (branch `main`), então o arquivo
sozinho basta. Antes de subir, aponte o registro A do domínio para o IP do VPS. Variáveis:

| Variável | Para quê |
| --- | --- |
| `DOMAIN` | Domínio público, sem `https://` (ex.: `esteira.exemplo.com.br`) |
| `DJANGO_SECRET_KEY` | Como acima |
| `POSTGRES_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` (sem caracteres especiais de URL) |

Para publicar uma nova versão, faça merge em `main` e reimplante com novo build
(`docker compose -f deploy/docker-compose.vps.yml up -d --build`, ou "Rebuild" no painel).
Para trazer dados de outra instalação: `python manage.py dumpdata --natural-foreign --natural-primary
-e contenttypes -e auth.permission -e admin.logentry -e sessions > dados.json` na origem e, no VPS,
`docker compose -f deploy/docker-compose.vps.yml exec -T web python manage.py loaddata --format=json - < dados.json`.

## Organização

```
esteira/
  domain/     regras em Python puro (sem Django)
  boards/     models, views, templates e arquivos estáticos
  tests/      domain/ (regras) e boards/ (aplicação)
```

As duas versões compartilham tudo, menos a política: `ClassicGUT` e `EnhancedGUT` em
`esteira/domain/scoring.py`, escolhidas por `Board.mode`.

Convenções do projeto: [`CLAUDE.md`](CLAUDE.md). Sistema visual: [`design.md`](design.md).
