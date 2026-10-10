# Prova Back-end ERP com IA

API em FastAPI para gestão de produtos e estoque. Este repositório está sendo
desenvolvido em incrementos verificáveis para a prova prática de backend.

## Estado atual

Marcos implementados:

- API FastAPI modular;
- PostgreSQL com SQLAlchemy assíncrono;
- migrações Alembic e seed idempotente de usuário;
- autenticação JWT com senha armazenada usando Argon2;
- CRUD completo de produtos, filtros e paginação;
- liveness, readiness e testes unitários/de integração.
- consulta concorrente a três fontes mock, com timeout individual, retry limitado e
  degradação parcial.

Ainda não estão implementados o cache Redis, worker de relatórios e agente
determinístico. Eles serão adicionados nos próximos marcos.

## Como executar com Docker

Requisitos: Docker Desktop com Docker Compose e porta 8000 disponível.

Crie a configuração local no PowerShell:

```powershell
Copy-Item .env.example .env
```

Antes de compartilhar ou publicar o projeto, troque `JWT_SECRET`, `SEED_PASSWORD` e
as senhas do PostgreSQL no `.env`. Esse arquivo está ignorado pelo Git.

Suba o ambiente:

```powershell
docker compose up --build
```

O serviço `bootstrap` aguarda o PostgreSQL, aplica as migrações e cria o usuário seed.
Depois disso, a API fica disponível em:

- Swagger: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness do PostgreSQL: `http://127.0.0.1:8000/health/ready`

Para acompanhar ou encerrar:

```powershell
docker compose ps
docker compose logs bootstrap api postgres
docker compose down
```

Os dados permanecem no volume `postgres_data` após `docker compose down`.

## Migrações e seed

O bootstrap executa estes comandos automaticamente:

```powershell
docker compose run --rm bootstrap alembic upgrade head
docker compose run --rm bootstrap python -m app.scripts.seed
```

O seed cria o usuário configurado por `SEED_USERNAME` somente quando ele ainda não
existe. Execuções posteriores não redefinem a senha.

## Autenticação e CRUD

Obtenha o token em `POST /api/v1/auth/token` usando o formulário OAuth2 do Swagger.
Clique em **Authorize** e informe `SEED_USERNAME` e `SEED_PASSWORD` do `.env`.

Rotas implementadas:

- `POST /api/v1/products`
- `GET /api/v1/products`
- `GET /api/v1/products/{id}`
- `PUT /api/v1/products/{id}`
- `PATCH /api/v1/products/{id}`
- `DELETE /api/v1/products/{id}`

A listagem aceita `page`, `page_size`, `nome`, `preco_min`, `preco_max`,
`estoque_abaixo_de` e `somente_sem_estoque`. Os filtros são combinados com `AND`.
O filtro de estoque usa comparação estrita: abaixo de 10 exclui produtos com saldo 10.

O preço usa `Decimal` e é devolvido como string com duas casas. Quantidade negativa,
preço negativo ou com mais de duas casas e nome sem letras são rejeitados.

## Consulta concorrente do ERP

`GET /api/v1/erp/overview` consulta simultaneamente três fontes mock: estoque,
financeiro e clientes. A rota exige JWT e identifica a resposta com `mode: "mock"`
para não apresentar os valores simulados como dados reais do PostgreSQL.

Com `DEMO_MODE=true`, o parâmetro `scenario` permite demonstrar:

- `success`: as três fontes respondem e o resultado é `complete`;
- `retry_success`: financeiro falha uma vez e se recupera na segunda tentativa;
- `partial_timeout`: financeiro esgota dois timeouts e os outros resultados são
  preservados com status `partial`;
- `all_failed`: as três fontes esgotam os timeouts e a API responde 503 com status
  `unavailable`.

Cada tentativa tem timeout de 600 ms. Apenas timeout e falha transitória são repetidos,
uma única vez, após espera de 100 ms. As fontes são iniciadas juntas com
`asyncio.gather`; uma falha não cancela as demais.

## Testes

Os testes rápidos podem ser executados no container da API:

```powershell
docker compose exec api python -m pytest -p no:cacheprovider
```

O teste de integração percorre login, proteção sem token, criação, consulta, filtros,
PATCH, PUT e exclusão contra a API e o PostgreSQL reais:

```powershell
docker compose exec `
  -e INTEGRATION_BASE_URL=http://localhost:8000 `
  api python -m pytest tests/integration -p no:cacheprovider
```

## Decisões deste marco

SQLAlchemy 2 assíncrono separa persistência dos casos de uso e mantém o acesso ao
PostgreSQL sem bloquear o event loop. Alembic registra a evolução do schema em vez de
criar tabelas implicitamente ao iniciar. O JWT tem duração curta e valida assinatura,
algoritmo, expiração, emissão e usuário ativo. Não existe cadastro público nesta prova;
o usuário demonstrativo é criado pelo seed.

## Uso de IA

Foi utilizada IA para apoiar a leitura do enunciado, estruturar o planejamento e
implementar a fundação, migração, autenticação, CRUD, consulta concorrente e testes
destes marcos. O candidato deve revisar o código, executar os comandos documentados e
compreender as decisões antes de cada commit. Esta seção será atualizada conforme o
desenvolvimento avançar.
