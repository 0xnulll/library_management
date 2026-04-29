# Neighborhood Library

Staff portal for a neighborhood library: track books, members, and borrow/return
operations. **Protobuf-driven gRPC backend** with a gRPC-Web frontend, packaged
with Docker Compose.

## Architecture

```
              gRPC-Web (HTTP/1.1)         gRPC (HTTP/2)
   browser  ─────────────────────►  Envoy  ─────────────────►  Python gRPC server
                                    :8000                       :50051
                                                                  │
                                                                  ▼
                                                              PostgreSQL
```

- All API contracts live in `proto/` (`auth`, `book`, `member`, `loan`, `common`).
- A single script (`scripts/gen_proto.sh`) regenerates **both** Python stubs
  (`backend/app/grpc_gen/`) and TypeScript stubs (`frontend/lib/proto/`).
- Generated stubs are committed; CI (`proto-drift` job) fails if they're stale.
- The browser talks gRPC-Web; Envoy translates to native gRPC for the backend.

## Known limitations / trade-offs:

- Generated Python gRPC modules currently depend on grpc_gen import-path setup (sys.path adjustment) due to protoc sibling import style.
- Default credentials and JWT secret are development defaults and must be overridden for production.
- Frontend local build/lint requires Node >= 18.17 (CI uses Node 20).

## Layout

```
proto/                       # source of truth for the API
backend/
  app/
    grpc_app/                # gRPC adapter
      servicers/             # one Servicer per .proto service
      converters/            # proto <-> domain mapping
      interceptors/          # JWT auth + domain-error -> gRPC status
      server.py              # build_server(...)
    grpc_gen/                # generated python (committed)
    services/                # application services (UNCHANGED)
    domain/                  # entities, exceptions, repository interfaces
    infrastructure/          # SQLAlchemy + concrete repositories
    main.py                  # asyncio entrypoint
  alembic/                   # migrations
  tests/                     # in-process gRPC component tests
envoy/envoy.yaml             # gRPC-Web filter + CORS
frontend/
  lib/
    proto/                   # generated ts-proto stubs (committed)
    grpc.ts                  # browser clients with JWT metadata
  app/                       # Next.js routes (login + dashboard)
scripts/
  gen_proto.sh               # regenerate py + ts stubs
  sample_client.py           # native-gRPC end-to-end client
docker-compose.yml           # db + backend + envoy + frontend
.github/workflows/ci.yml
```

## Run with Docker

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Envoy (gRPC-Web for browser) | http://localhost:8000 |
| Native gRPC | localhost:50051 |
| Postgres | localhost:5432 |
| Envoy admin | http://localhost:9901 |

Default staff credentials: `admin` / `admin` (override via `ADMIN_USERNAME` /
`ADMIN_PASSWORD` env). On first boot the backend runs `alembic upgrade head`
and seeds the admin user.

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL="postgresql+psycopg://library:library@localhost:5432/library"
export JWT_SECRET="dev-secret"
alembic upgrade head
python -m app.main
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

## Regenerate stubs after editing a proto

```bash
./scripts/gen_proto.sh
```

This calls `protoc` once for Python (`grpc_tools.protoc`) and once for
TypeScript (`protoc-gen-ts_proto` from `frontend/node_modules`). Both outputs
are committed; CI rejects PRs that forget to regenerate.

## Tests & lint

```bash
cd backend
ruff check .
pytest -q
```

The component suite spins up an in-process `grpc.aio` server, talks to it via
the generated stubs, and exercises:

- login + `Me` + invalid token rejection
- protected RPCs without a token return `UNAUTHENTICATED`
- create/search book, validation errors return `INVALID_ARGUMENT`
- duplicate-email member returns `FAILED_PRECONDITION`
- happy-path borrow/return updates `available_copies`
- double-borrow on a single-copy book returns `FAILED_PRECONDITION`
- a threaded race test at the service layer that proves only one of two
  simultaneous borrowers wins (uses file-backed SQLite with `BEGIN IMMEDIATE`
  to mirror Postgres write-lock semantics).

## Concurrency model

`LoanService.borrow` acquires an exclusive row lock on the target book before
counting active loans, so two staff trying to lend the last copy at the same
instant are serialized:

- on Postgres: `SELECT … FOR UPDATE` on `books`;
- on SQLite (test path): a no-op `UPDATE` on the row, with the engine
  configured for `BEGIN IMMEDIATE`.

The loser surfaces `FAILED_PRECONDITION` with `details = "no copies
available"`. The same path also blocks a member from borrowing the same title
twice without returning it first.

## Sample client

`scripts/sample_client.py` drives the API end-to-end via native gRPC:

```bash
python scripts/sample_client.py --target 127.0.0.1:50051
```

## RPC quick reference

| Service | RPC | Purpose |
| --- | --- | --- |
| `library.auth.AuthService` | `Login` | exchange username/password for JWT |
| | `Me` | inspect current user |
| | `Logout` | client-side token discard (server stateless) |
| `library.book.BookService` | `CreateBook` / `UpdateBook` / `GetBook` | manage books |
| | `SearchBooks` | full-text search by title/author/ISBN |
| `library.member.MemberService` | `CreateMember` / `UpdateMember` / `GetMember` / `ListMembers` | manage members |
| `library.loan.LoanService` | `Borrow` / `ReturnLoan` | record loan transitions |
| | `ListLoans` / `ListLoansByMember` | query loans |

Every RPC except `AuthService.Login` requires `authorization: Bearer <jwt>`
metadata.

## Status mapping

| Domain exception | gRPC status |
| --- | --- |
| `NotFoundError` | `NOT_FOUND` |
| `ConflictError` | `FAILED_PRECONDITION` |
| `AuthenticationError` | `UNAUTHENTICATED` |
| `ValidationError` | `INVALID_ARGUMENT` |

## Configuration

Environment variables read by the backend (`backend/app/core/config.py`):

| Var | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://library:library@localhost:5432/library` | SQLAlchemy URL |
| `JWT_SECRET` | `change-me-in-production` | HMAC signing key |
| `JWT_EXPIRES_MINUTES` | `480` | Access-token lifetime |
| `DEFAULT_LOAN_DAYS` | `14` | Loan due-date offset |
| `GRPC_BIND` | `0.0.0.0:50051` | gRPC listener |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin` | Seed staff user |


## TODO / Scope of Improvement

- Redis improvement for caching
- Structured logging (request id / method / latency) and metrics (RPC count, errors, DB pool) 
- PgBouncer for scaling/pooling connection
- Load testing
