# Data Model: Item Categories

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) | **Date**: 2026-11-23

All models live in `backend/app/models.py` and follow the constitution's schema split
(Principle III).

## Entity relationships

```text
User 1 ──< Category        (owner_id, ON DELETE CASCADE)
User 1 ──< Item            (owner_id, ON DELETE CASCADE)   [existing]
Category 1 ──< Item        (category_id, nullable, ON DELETE SET NULL)

Invariant: item.category_id IS NULL OR category.owner_id = item.owner_id
```

The invariant is enforced in the application (R6). A composite foreign key could enforce it in
the database, but that is deliberately not used because it would complicate `SET NULL`.

## Category (new table `category`)

| Field | Type | Constraints | Source |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4` | pattern from `Item` |
| `name` | VARCHAR(255) | NOT NULL; 1–255 chars after trimming | FR-002 |
| `owner_id` | UUID | NOT NULL; FK → `user.id` ON DELETE CASCADE (lookups served by the unique index below) | FR-001, account deletion edge case |
| `created_at` | timestamp (UTC) | default now, same definition as `Item.created_at` | pattern from `Item` |

**Indexes**

- `uq_category_owner_id_lower_name`: UNIQUE on `(owner_id, lower(name))` (FR-003, R2)

**Relationships**

- `Category.owner → User` (back_populates `User.categories`, `cascade_delete=True`, matching
  `User.items`)
- No `Category.items` back-reference (R4)

## Item (existing table `item`, changed)

| Field | Change | Constraints | Source |
|---|---|---|---|
| `category_id` | **added** | UUID, NULL; FK → `category.id` ON DELETE SET NULL; index `ix_item_category_id` | FR-005–FR-007, FR-010 |
| `category` | **added** relationship | `Item.category → Category \| None` (one-way) | R5 |

Existing rows get `category_id = NULL`. No backfill is needed (FR-013).

## User (existing, changed)

- Gains a `categories: list[Category]` relationship (`back_populates="owner"`,
  `cascade_delete=True`).

## Schemas (Pydantic / SQLModel, non-table)

| Schema | Fields | Notes |
|---|---|---|
| `CategoryBase` | `name: str` (`min_length=1`, `max_length=255`) | shared |
| `CategoryCreate` | inherits `CategoryBase` | `field_validator("name", mode="before")` strips whitespace (R3) |
| `CategoryPublic` | `id`, `name`, `owner_id`, `created_at` | response model |
| `CategoriesPublic` | `data: list[CategoryPublic]`, `count: int` | collection response |
| `ItemCreate` | **+** `category_id: uuid.UUID \| None = None` | optional (FR-005, FR-007) |
| `ItemUpdate` | **+** `category_id: uuid.UUID \| None = None` | explicit `null` clears; omitted means unchanged (R7) |
| `ItemPublic` | **+** `category_id: uuid.UUID \| None`, **+** `category: CategoryPublic \| None` | FR-008, FR-009 (R5) |

There is no `CategoryUpdate` because renaming is out of scope.

## Validation rules

| Rule | Where | Result on failure |
|---|---|---|
| Name is 1–255 chars after trimming | `CategoryCreate` | `422` |
| Name unique per owner, ignoring case | CRUD pre-check plus unique index | `409 "A category with this name already exists"` |
| `category_id` on an item exists and has the same owner as the item | items create and update routes | `400 "Category not found"`; item unchanged |
| Only the owner may delete a category (no superuser bypass) | categories delete route | `403 "Not enough permissions"` |

## State transitions (Item → category)

```text
uncategorized ──assign (create/edit)──▶ categorized(c)
categorized(c) ──change (edit)───────▶ categorized(c')
categorized(c) ──clear (edit, null)──▶ uncategorized
categorized(c) ──delete category c───▶ uncategorized        (DB SET NULL)
```

## Migration

One Alembic revision, `down_revision = "fe56fa70289e"`.

**upgrade()**

1. Create the `category` table with the named FK `category_owner_id_fkey`.
2. Create the unique index `uq_category_owner_id_lower_name` on `(owner_id, lower(name))`.
3. Add the nullable `item.category_id` column.
4. Create the FK `item_category_id_fkey` with ON DELETE SET NULL.
5. Create the index `ix_item_category_id`.

**downgrade()**

Reverse order: drop the index, FK and column on `item`, then drop the unique index and the
`category` table.

See R9 for why names are set by hand.
