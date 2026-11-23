<!--
Sync Impact Report
==================
Version change: 1.0.0 → 2.0.0
Bump rationale: MAJOR. Core principles restructured from five to the four specified by the
project owner; two principles were removed as principles and one was redefined.

Modified principles:
- I. Typed Contracts End-to-End → III. Typing & Validation (Pydantic schemas for all I/O)
- III. Tested Against Real Infrastructure → IV. Feature Testing: Backend, API, and E2E
  (expanded: E2E tests now required for every feature, not only changed UI flows)
- IV. Schema Changes Through Migrations → II. Database Changes Only Through Migrations
- (new) I. Backend First (absorbs the generated-client rules formerly in old Principle I)

Removed principles (rules preserved elsewhere, not dropped):
- II. Secure by Default → moved to "Technology Stack & Constraints" (Security bullets)
- V. Automated Quality Gates & Simplicity → moved to "Development Workflow & Quality Gates"

Added sections: none (Section 3 renamed "Development Workflow & Review" →
"Development Workflow & Quality Gates"; Docker-first constraint added to Section 2)

Removed sections: none

Templates reviewed (read at runtime, not modified by this command):
- .specify/templates/plan-template.md: "Constitution Check" gate reads this file ✅ compatible
- .specify/templates/spec-template.md: no constitution-specific slots ✅ compatible
- .specify/templates/tasks-template.md: ⚠ marks tests "OPTIONAL" and uses generic paths
  (tests/contract/, tests/integration/). Principle IV overrides: /speckit-tasks MUST emit
  backend, API, and E2E test tasks under backend/tests/crud/, backend/tests/api/routes/,
  frontend/tests/. Principle I additionally requires backend tasks to precede frontend tasks
  within each user story.

Deferred TODOs: none (template wording conflict above is resolved by precedence, see Governance)
-->

# Full Stack FastAPI Template Constitution

A full-stack application with a FastAPI backend and a React frontend, run with Docker Compose.

## Core Principles

### I. Backend First

The backend is the system of record; the frontend is a client of it.

- Every feature MUST be built backend first: models, migration, CRUD, routes, and their tests
  are completed before frontend work on that feature begins. In `tasks.md`, backend tasks for
  a user story MUST precede that story's frontend tasks.
- A feature's API MUST be fully usable and verifiable on its own (via tests and the OpenAPI
  docs at `/docs`) before any UI depends on it.
- Business rules, validation, and authorization MUST be enforced in the backend. Frontend
  validation is a usability aid only and MUST NOT be the sole check for any rule.
- The frontend MUST call the API only through the generated client in `frontend/src/client`.
  That client MUST NOT be edited by hand and MUST be regenerated (`scripts/generate-client.sh`)
  and committed in the same change as any backend modification that alters the OpenAPI schema.

**Rationale**: A stable, tested API gives the frontend a fixed contract to build against,
keeps rules in one place, and leaves the backend usable by other clients.

### II. Database Changes Only Through Migrations

- Every change to a `table=True` model MUST ship with an Alembic revision generated via
  `alembic revision --autogenerate`, reviewed by hand, and committed with the model change.
- `SQLModel.metadata.create_all`, manual SQL against shared databases, or any other
  out-of-band schema change MUST NOT be used to evolve the schema.
- Migrations MUST apply cleanly from the current head (`alembic upgrade head`, run by
  `scripts/prestart.sh`) and MUST implement a working `downgrade()`.
- Adding a non-nullable column to an existing table MUST provide a server default or a data
  backfill so the migration succeeds on populated databases.
- Foreign keys MUST declare deletion behavior explicitly (e.g. `ondelete="CASCADE"` or
  `"SET NULL"`).

**Rationale**: Migrations make schema history reproducible across local, CI, and deployed
environments; hand review catches what autogenerate misses (renames, data moves).

### III. Typing & Validation

Every request and response crossing the API boundary MUST be described by a Pydantic schema.

- Request bodies MUST be Pydantic/SQLModel schemas. Endpoints MUST NOT accept untyped input
  (`dict`, `Any`, or raw `Request.json()`). Path and query parameters MUST be typed.
- Every endpoint MUST declare a `response_model` that is a `Public` schema (or `Message`).
  Table models, and fields such as `hashed_password`, MUST NOT be returned directly.
- Schemas MUST follow the established split in `backend/app/models.py`: `<Entity>Base`,
  `<Entity>Create`, `<Entity>Update` (all fields optional), the `table=True` model, and
  `<Entity>Public` / `<Entity>sPublic`.
- Fields MUST carry explicit constraints (`max_length`, `min_length`, `ge`/`le`, `EmailStr`,
  etc.) that match the database column, so invalid input is rejected with `422`.
- Collection endpoints MUST accept `skip` / `limit` and return `{ data: [...], count: int }`.
- Backend code MUST pass mypy (`strict = true`) and ty (warnings are errors). Frontend code
  MUST pass TypeScript `strict` checks and use the generated client types.

**Rationale**: Schemas are the API contract; they drive validation, OpenAPI docs, and the
generated frontend types, so a mismatch fails at build time instead of in production.

### IV. Feature Testing: Backend, API, and E2E (NON-NEGOTIABLE)

Every feature MUST ship with all three test layers:

- **Backend tests**: CRUD and domain logic tested directly in `backend/tests/crud/` (and
  helpers in `backend/tests/utils/`).
- **API tests**: every new or changed endpoint tested through the HTTP layer in
  `backend/tests/api/routes/`, covering the happy path, validation failure (`422`), not found
  (`404`), unauthenticated access, and permission denied (`403`, for non-owners and
  non-superusers).
- **E2E tests**: Playwright specs in `frontend/tests/` covering the feature's primary user
  journeys through the UI against the running Docker Compose stack.

Additional rules:

- Backend and API tests MUST run against the real PostgreSQL service from Docker Compose; the
  database layer MUST NOT be mocked.
- Backend line coverage MUST stay at or above **90%** (`coverage report --fail-under=90` in CI).
- A feature with no user-facing surface MAY omit E2E tests only if the plan records the
  exemption and its reason in Complexity Tracking.

**Rationale**: Each layer catches a different class of defect (logic, contract, integration);
requiring all three per feature prevents coverage gaps from building up.

## Technology Stack & Constraints

- **Backend**: Python 3.14, FastAPI, SQLModel, Pydantic v2, PostgreSQL (psycopg 3), Alembic,
  PyJWT, pwdlib; managed with `uv`.
- **Frontend**: React + TypeScript, Vite, TanStack Router, TanStack Query, Tailwind CSS,
  shadcn/ui; managed with Bun; linted with Biome.
- **Docker**: The whole stack MUST run with Docker Compose (`compose.yml` +
  `compose.override.yml` locally, `compose.deploy.yml` for deployment). Any new service or
  infrastructure dependency MUST be added to the Compose files; features MUST NOT require
  services that run only outside Docker.
- **Email**: Templates are authored in React Email (`packages/react-email/`). The rendered HTML
  in `backend/app/email-templates/` is generated output and MUST NOT be edited by hand.
- **Security**:
  - Every endpoint MUST require authentication via `CurrentUser` (or
    `get_current_active_superuser`) unless it belongs to the public auth flow (login, signup,
    password recovery) and the spec states the exception.
  - User-owned resources MUST enforce ownership: non-superusers receive `403` for another
    user's resource, and list endpoints filter by `owner_id` for non-superusers.
  - Passwords MUST be hashed via `app.core.security` (pwdlib).
  - Secrets MUST come from settings/environment; `changethis` MUST NOT reach non-local
    environments, and deployment secrets MUST NOT be committed to `.env`.
- Replacing any of the above with a different framework, datastore, or runtime is a
  governance change and requires a constitution amendment.

## Development Workflow & Quality Gates

- Work happens on feature branches off `master` and merges through pull requests.
- Non-trivial features SHOULD follow the Spec Kit flow: `/speckit-specify` → `/speckit-plan`
  → `/speckit-tasks` → `/speckit-implement`. The plan's Constitution Check gate MUST pass
  before research and again after design.
- All `prek` hooks in `.pre-commit-config.yaml` MUST pass: ruff (lint + format), mypy, ty,
  Biome, typos, and zizmor for workflows. `print` is forbidden in backend code (ruff `T201`).
- New code MUST follow the existing layering: models in `app/models.py`, data access in
  `app/crud.py`, HTTP concerns in `app/api/routes/`, shared dependencies in `app/api/deps.py`.
  New abstraction layers or runtime dependencies MUST be justified in the plan's Complexity
  Tracking; changes to `pyproject.toml` or `uv.lock` are treated as supply-chain-sensitive.
- PRs MUST be focused on a single change and MUST pass all CI workflows (backend tests with
  coverage gate, Playwright, pre-commit, zizmor) before merge.
- AI-assisted contributions are permitted but MUST receive meaningful human review; the author
  is accountable for every line submitted.
- Release-relevant changes SHOULD be recorded in `release-notes.md`.

## Governance

This constitution supersedes informal conventions. Where it conflicts with other docs or
templates, the constitution wins and the other docs MUST be updated.

- **Amendments**: Proposed by PR modifying `.specify/memory/constitution.md`, including a Sync
  Impact Report, and approved by a maintainer before merge.
- **Versioning**: Semantic versioning. MAJOR for removing or redefining a principle; MINOR for
  adding a principle or section or materially expanding guidance; PATCH for clarifications and
  wording fixes.
- **Compliance**: Every plan MUST complete the Constitution Check; any violation MUST be
  recorded with justification in Complexity Tracking or the plan is blocked. Reviewers MUST
  verify compliance during PR review.
- **Runtime guidance**: Day-to-day how-to lives in `development.md`, `backend/README.md`, and
  `frontend/README.md`.

**Version**: 2.0.0 | **Ratified**: 2026-11-23 | **Last Amended**: 2026-11-23
