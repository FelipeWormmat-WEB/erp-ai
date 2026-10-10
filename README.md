# Prova Back-end ERP com IA

API em FastAPI para gestao de produtos e estoque, criada para a prova pratica de
backend. A entrega demonstra CRUD com PostgreSQL, autenticacao JWT, cache Redis,
consulta concorrente a fontes mock, processamento em fila e um agente
deterministico de consulta em linguagem natural.

## Estado atual

Implementado:

- API FastAPI modular, com rotas versionadas em `/api/v1`;
- PostgreSQL com SQLAlchemy assincrono, Alembic e seed idempotente;
- autenticacao JWT com senha armazenada usando Argon2;
- CRUD completo de produtos, validacoes, filtros e paginacao;
- cache Redis no detalhe de produto, com TTL, `X-Cache` e invalidacao apos escrita;
- consulta concorrente a tres fontes mock, com timeout individual, retry limitado e
  degradacao parcial;
- worker `arq` em processo separado para relatorio de estoque baixo;
- agente deterministico somente leitura para perguntas suportadas;
- healthchecks, Docker Compose e testes unitarios/de integracao.

Limites conhecidos:

- os dados do endpoint `/erp/overview` sao mockados para demonstrar concorrencia;
- a consistencia do cache e eventual, com TTL de 60 segundos por padrao;
- nao ha outbox automatica para relatorios: existe script manual para reenfileirar
  pendentes antigos;
- nao ha frontend, deploy em nuvem, refresh token, multitenancy ou LLM externo.

## Como executar com Docker

Requisitos: Docker Desktop com Docker Compose e porta 8000 disponivel.

Crie a configuracao local no PowerShell:

```powershell
Copy-Item .env.example .env
```

Antes de publicar o projeto, troque `JWT_SECRET`, `SEED_PASSWORD` e
`POSTGRES_PASSWORD` no `.env`. O arquivo `.env` esta ignorado pelo Git.

Suba o ambiente:

```powershell
docker compose up --build
```

O `bootstrap` aguarda o PostgreSQL, aplica as migracoes e cria o usuario seed. Depois
disso, a API fica disponivel em:

- Swagger: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness: `http://127.0.0.1:8000/health/ready`

Comandos uteis:

```powershell
docker compose ps
docker compose logs bootstrap api worker postgres redis
docker compose down
```

Os dados ficam nos volumes `postgres_data` e `redis_data` depois do `down`.

## Autenticacao

Obtenha um token em `POST /api/v1/auth/token` usando o formulario OAuth2 do Swagger.
Depois clique em **Authorize** e informe `SEED_USERNAME` e `SEED_PASSWORD` do `.env`.

Todas as rotas de dominio exigem `Authorization: Bearer <token>`.

## Produtos e cache

Rotas:

- `POST /api/v1/products`
- `GET /api/v1/products`
- `GET /api/v1/products/{id}`
- `PUT /api/v1/products/{id}`
- `PATCH /api/v1/products/{id}`
- `DELETE /api/v1/products/{id}`

A listagem aceita `page`, `page_size`, `nome`, `preco_min`, `preco_max`,
`estoque_abaixo_de` e `somente_sem_estoque`. Os filtros sao combinados com `AND`; o
filtro de estoque e estrito, entao abaixo de 10 exclui produtos com saldo 10.

`GET /products/{id}` usa cache-aside no Redis. A resposta inclui `X-Cache: MISS`,
`HIT` ou `BYPASS`. `PUT`, `PATCH` e `DELETE` confirmam a transacao no PostgreSQL e
depois invalidam a chave do produto. Se o Redis falhar, a API consulta o PostgreSQL e
nao transforma a falha de cache em erro 500.

PostgreSQL continua sendo a fonte de verdade. Redis acelera leitura, mas nao decide
baixa de estoque nem autoriza operacoes de dominio.

## Consulta concorrente do ERP

`GET /api/v1/erp/overview` consulta simultaneamente tres fontes mock: estoque,
financeiro e clientes. A resposta usa `mode: "mock"` para deixar claro que os valores
nao sao dados reais do PostgreSQL.

Com `DEMO_MODE=true`, o parametro `scenario` permite demonstrar:

- `success`: as tres fontes respondem e o resultado e `complete`;
- `retry_success`: financeiro falha uma vez e se recupera na segunda tentativa;
- `partial_timeout`: financeiro esgota dois timeouts e os outros resultados sao
  preservados com status `partial`;
- `all_failed`: as tres fontes falham e a API responde 503 com status `unavailable`.

Cada tentativa tem timeout de 600 ms. Apenas timeout e falha transitoria sao repetidos,
uma unica vez, apos espera de 100 ms. As fontes sao iniciadas juntas com
`asyncio.gather`.

## Relatorios em fila

`POST /api/v1/reports/low-stock` cria um relatorio `pending`, confirma no PostgreSQL e
publica um job no Redis para o worker `arq`. A resposta de sucesso e `202` com
`report_id` e `status_url`.

`GET /api/v1/reports/{id}` retorna o estado e, quando concluido, o retrato dos produtos
com `quantidade_em_estoque < threshold`. O resultado e persistido no PostgreSQL.

Se a publicacao na fila falhar depois do registro ser salvo, a API retorna `503` com
`REPORT_QUEUE_UNAVAILABLE` e o `report_id`. Como nao existe transacao atomica entre
PostgreSQL e Redis, pendentes antigos podem ser reenfileirados manualmente:

```powershell
docker compose exec api python -m app.scripts.requeue_pending_reports
```

O worker protege reexecucoes pelo estado do relatorio no banco: um relatorio
`completed` nao e recalculado.

## Agente deterministico

`POST /api/v1/agent/query` interpreta perguntas em portugues e executa apenas a
ferramenta local allowlisted `consultar_produtos`. O agente nao usa LLM externo, nao
executa SQL vindo do usuario e nao permite escrita.

Perguntas suportadas:

- `Quais produtos estao com estoque abaixo de 10 unidades?`
- `Quais produtos estao sem estoque?`
- `Quais produtos custam entre 20 e 100 reais?`

Ambiguidade, falta de limite, negacao ou formulacoes fora do contrato retornam
`needs_clarification`. Pedidos como excluir, alterar, cadastrar ou remover retornam
`rejected`.

## Testes

Testes rapidos:

```powershell
.\venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

Com Docker/API rodando, execute a integracao real:

```powershell
docker compose exec `
  -e INTEGRATION_BASE_URL=http://localhost:8000 `
  api python -m pytest tests/integration -p no:cacheprovider
```

Esses testes percorrem login, protecao sem token, CRUD, cache, overview concorrente,
worker de relatorio e agente consultando dados reais.

## Q1 - Arquitetura ERP

Para um ERP maior, eu separaria os dominios por responsabilidade: Clientes, Produtos e
Estoque, Pedidos e Financeiro. Cada servico seria dono das suas gravacoes e do seu
schema. Consultas ou comandos sincronicos usariam REST com timeout e correlacao;
processos que podem finalizar depois usariam eventos, outbox e consumidores
idempotentes.

PostgreSQL seria a fonte de verdade para saldos, pedidos e financeiro. Redis poderia
servir cache, rate limit e fila em cenarios simples, mas nao substituiria transacoes de
dominio. Um gateway cuidaria de entrada, TLS, roteamento, quotas e autenticacao de
borda, sem concentrar regras de negocio. Em AWS, uma evolucao plausivel seria API e
worker em ECS/Fargate, imagem no ECR, PostgreSQL no RDS, Redis gerenciado e logs no
CloudWatch.

## Q2 - Camadas

A aplicacao usa routers para HTTP, schemas Pydantic para contrato, services para casos
de uso, repositories para SQLAlchemy, models para mapeamento, integrations para Redis,
fila e fontes externas, e workers para processamento assincrono. Essa separacao permite
testar parser sem banco, testar regras de schema isoladas e testar persistencia com
PostgreSQL real quando necessario.

## Q3 - Concorrencia

`asyncio` e adequado para I/O concorrente, como consultar tres fontes de ERP com espera
de rede. `threading` pode ajudar com SDKs bloqueantes ou bibliotecas legadas de I/O,
desde que haja limites de pool e timeout. `multiprocessing` faz sentido quando o gargalo
e CPU, por exemplo transformacao pesada ou relatorio computacional. Para esta prova, a
Q4 e I/O simulado; por isso o endpoint usa `asyncio`.

## Q4 - Falhas parciais

O overview inicia as tres fontes juntas, limita cada tentativa, repete apenas falhas
transitorias e preserva os resultados saudaveis. Se uma fonte falha, a resposta pode ser
`partial`; se todas falham, retorna 503. Isso evita transformar uma dependencia lenta em
falha total da tela.

## Q6 - Persistencia, ORM, Redis e worker

Pydantic valida entradas no limite HTTP; SQLAlchemy mapeia entidades e consultas; o
PostgreSQL aplica constraints basicas e guarda a verdade transacional. O ORM reduz
repeticao e melhora composicao de consultas, mas nao elimina a necessidade de pensar em
indices, transacoes e SQL gerado.

Redis aparece em dois papeis separados: cache de detalhe de produto e transporte dos
jobs do `arq`. Em producao, eu avaliaria separar essas responsabilidades em instancias
ou politicas diferentes.

## Q7 - Containers e segredos

O Compose sobe PostgreSQL, Redis, bootstrap, API e worker. O bootstrap aplica Alembic e
seed uma vez; API e worker so iniciam depois dele. Segredos ficam no `.env`, nao na
imagem. Healthchecks diferenciam processo vivo, banco pronto e Redis indisponivel.

## Q8 - Linguagem natural

O agente separa interpretacao e execucao. O interpretador transforma perguntas
suportadas em plano estruturado; o executor revalida os argumentos e chama o mesmo
`ProductService` usado pela API. Perguntas destrutivas sao rejeitadas antes de qualquer
consulta ou escrita.

## Q9 - IA, tools e MCP

Uma evolucao com LLM manteria o mesmo contrato de ferramenta: o modelo poderia sugerir
`consultar_produtos`, mas o backend continuaria validando schema, identidade,
permissoes, limites e allowlist. O usuario nao escolheria SQL, tenant ou papel via
prompt. MCP poderia expor ferramentas do ERP para diferentes clientes de agente, mas o
servidor MCP seria so um adaptador autenticado para os servicos de dominio, nao acesso
direto aos bancos.

## Q10 - Go

Eu avaliaria Go pelo problema, nao por preferencia pessoal. Para um servico de ingestao
concorrente ou workload com alta pressao de CPU/memoria, Go pode ser uma boa escolha.
Eu compararia throughput, p95/p99, memoria, gargalo real, bibliotecas e maturidade da
equipe. Se o gargalo estiver no banco, rede ou desenho da fila, trocar a linguagem pode
nao resolver. Minha abordagem seria entregar uma fatia vertical pequena, medir e revisar
com alguem experiente na stack.

## Q11 - Portfolio

Preencher com links reais antes do envio. O ideal e escolher um projeto cujo codigo
possa ser acessado e explicado: problema resolvido, minha participacao, decisoes
tecnicas, resultado observado e uma melhoria concreta que eu faria hoje. Nao incluir
codigo privado nem metricas inventadas.

## Uso de IA

Foi utilizada IA para apoiar a leitura do enunciado, estruturar o planejamento, revisar
arquitetura, implementar codigo, ampliar documentacao e apontar lacunas. O codigo foi
organizado para continuar verificavel por testes e por execucao local. Antes do envio, o
candidato deve rodar os comandos documentados e revisar as respostas em primeira pessoa,
especialmente Q10 e Q11.
