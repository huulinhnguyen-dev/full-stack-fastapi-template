# Research: Item Categories

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-23

The spec and the constitution left no open questions. This file records the design decisions
behind the plan.

## R1. ORM layer: "SQLAlchemy" in the request vs. SQLModel in the codebase

- **Decision**: Model the data with **SQLModel 0.0.47**, which is built on **SQLAlchemy 2.0.51**.
  Where SQLModel has no wrapper, use SQLAlchemy constructs directly: `Index`, `func.lower`,
  `selectinload`.
- **Rationale**: The constitution (Principle III, Technology Stack) requires SQLModel and the
  `Base/Create/Update/Public` split. SQLModel table models are SQLAlchemy mapped classes, so this
  satisfies the "SQLAlchemy" request without a second modeling style.
- **Alternatives considered**: Plain SQLAlchemy declarative models with separate Pydantic schemas.
  Rejected because it would duplicate every field and break the pattern used by `User` and `Item`.

## R2. Case-insensitive unique category names per owner (FR-003)

- **Decision**: Add a **functional unique index** on `(owner_id, lower(name))`, declared in
  `Category.__table_args__`. The create endpoint also checks for a duplicate with
  `func.lower(Category.name) == name.lower()` and returns `409`. An `IntegrityError` on commit
  also maps to `409` as a backstop for races. `owner_id` gets no separate index, because this
  index's leading column already serves owner lookups and the `ON DELETE CASCADE` check.
- **Rationale**: The database guarantees the rule under concurrency. The pre-check gives users a
  clear message in the normal case. Names keep the casing the user typed.
- **Alternatives considered**:
  - `citext` column type: needs a Postgres extension and complicates migrations and tests.
  - A separate `normalized_name` column: duplicated data that must be kept in sync.
  - An application-only check: has a race window and no DB guarantee.

## R3. Name trimming (FR-002)

- **Decision**: Add a `field_validator("name", mode="before")` on `CategoryCreate` that strips
  surrounding whitespace before the `min_length=1` / `max_length=255` constraints run, so `"   "`
  is rejected with `422`.
- **Rationale**: Keeps validation in the schema (Principle III), so the OpenAPI contract and error
  shape match every other validation error.
- **Alternatives considered**: Trimming in the route or CRUD layer. Rejected because it would let
  whitespace-only names pass schema validation and fail later with a less clear error.

## R4. Deleting a category leaves items uncategorized (FR-010)

- **Decision**: Use a foreign key `item.category_id → category.id` with **`ON DELETE SET NULL`**,
  indexed. `Item.category` is a one-way relationship. `Category` has **no** `items` back-reference,
  so the database nulls the references.
- **Rationale**: One atomic statement with no ORM loading of affected items. It can't leave
  dangling references, and the index keeps the `SET NULL` cheap.
- **Alternatives considered**:
  - Blocking deletion while the category is in use: contradicts User Story 3.
  - ORM-side nulling through a back-populated relationship: loads every affected item into memory.

## R5. How items expose their category (FR-008, FR-009)

- **Decision**: `ItemPublic` gains `category_id: uuid.UUID | None` and a nested
  `category: CategoryPublic | None`. The list endpoint eager-loads the relationship with
  `selectinload(Item.category)`. One extra query per page avoids N+1 lookups.
- **Rationale**: Administrators see other users' items (spec edge case) but cannot list those
  users' categories. The item response must therefore carry the category name itself.
  `category_id` lets the edit form preselect the current value.
- **Alternatives considered**:
  - Return only `category_id` and join in the frontend: fails for administrators.
  - A flat `category_name` string: loses the id the edit form needs.

## R6. Rejecting an invalid category assignment (FR-011)

- **Decision**: Item create and update check that `category_id` exists **and**
  `category.owner_id == item.owner_id`. Otherwise they return **`400 {"detail": "Category not
  found"}`** and change nothing.
- **Rationale**: One response for "doesn't exist" and "belongs to someone else", so other users'
  category ids aren't revealed. 400 keeps it distinct from the `404 "Item not found"` that the
  same `PUT /items/{id}` route uses.
- **Alternatives considered**:
  - `404`: ambiguous with item not found.
  - `403`: confirms the category exists.
  - `422`: FastAPI reserves that shape for schema validation errors.

## R7. Clearing an item's category (User Story 2)

- **Decision**: Keep the existing `model_dump(exclude_unset=True)` semantics on `ItemUpdate`. An
  explicit `"category_id": null` clears the category, and omitting the field leaves it unchanged.
  The edit form always sends `category_id`, as `null` when "No category" is selected.
- **Rationale**: No new endpoint; this matches the current partial update behavior.
- **Alternatives considered**: A dedicated `DELETE /items/{id}/category` endpoint. Rejected as
  extra surface for something one field already expresses.

## R8. Administrators and categories (spec Clarifications Q1; FR-001)

- **Decision**: Category endpoints **have no superuser bypass**: list returns only the caller's
  categories, and deleting another user's category returns `403` even for superusers. R6's rule
  applies to administrators editing other users' items. In the UI, when the current user does not
  own the item being edited, the category picker offers only "No category" and the item's current
  category.
- **Rationale**: Implements "categories are always personal" while keeping the constitution's
  ownership rule (403 for another user's resource).
- **Alternatives considered**: Letting the picker show the administrator's own categories.
  Rejected because every such choice would be rejected by the backend.

## R9. Migration hygiene (Principle II)

- **Decision**: One Alembic revision, autogenerated and then hand-edited so that:
  1. the functional unique index is present, since autogenerate may not emit expression indexes
     reliably;
  2. constraints and indexes are **named explicitly** (`category_owner_id_fkey`,
     `item_category_id_fkey`, `ix_item_category_id`, `uq_category_owner_id_lower_name`) so
     `downgrade()` can drop them.

  Its `down_revision` is the current head, `fe56fa70289e`.
- **Rationale**: Autogenerate writes `op.drop_constraint(None, …)` for unnamed constraints, which
  fails on downgrade. Migration `1a31ce608336` already fixed this by hand.
- **Alternatives considered**: `SQLModel.metadata.create_all`, which the constitution forbids.

## R10. Frontend category picker and cache invalidation

- **Decision**: A shared `CategorySelect` component built on the existing shadcn `Select`. The
  "No category" option uses the sentinel value `"none"`, mapped to `null` on submit. A Radix
  Select item can't have `""` as its value. Categories load with the query key `["categories"]`.
  Creating or deleting a category invalidates `["categories"]`; deleting also invalidates
  `["items"]` so affected rows show "No category" straight away.
- **Rationale**: Reuses existing UI primitives and the TanStack Query patterns from the Items
  components. No new dependencies (Principle V / Development Workflow).
- **Alternatives considered**: A combobox with type-to-create. Rejected because creating from the
  item form is out of scope (Clarifications Q2).

## R11. Test data cleanup

- **Decision**: The session teardown in `backend/tests/conftest.py` deletes `Category` rows after
  `Item` and before `User`. A new helper, `backend/tests/utils/category.py`, mirrors
  `tests/utils/item.py`.
- **Rationale**: Matches the existing teardown pattern, so the shared test database stays clean
  across runs.
