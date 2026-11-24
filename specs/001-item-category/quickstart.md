# Quickstart: Validate Item Categories

How to prove the feature works end to end. Run the commands from the repository root unless a
step says otherwise. Data shapes are in [data-model.md](./data-model.md). Endpoint behavior is in
[contracts/](./contracts/).

## Prerequisites

- Docker, `uv`, Bun (see [development.md](../../development.md))
- Dependencies installed: `uv sync` (in `backend/`) and `bun install` (repo root)

## 1. Migration applies, reverts, and re-applies cleanly (Principle II)

```bash
docker compose up -d db mailpit
cd backend
uv run alembic upgrade head        # applies the new revision on top of fe56fa70289e
uv run alembic downgrade -1        # removes item.category_id and the category table
uv run alembic upgrade head        # re-applies without errors
uv run alembic check               # "No new upgrade operations detected."
```

**Expected**:
- All four commands succeed. If `alembic check` reports a diff **only** for the functional index
  `uq_category_owner_id_lower_name`, that is an Alembic comparison limitation with expression
  indexes (research R9). Confirm the index exists and record it in the PR.
- After the upgrade, `\d category` in `docker compose exec db psql -U postgres app` shows the
  `uq_category_owner_id_lower_name` index.
- `\d item` shows `category_id` with `ON DELETE SET NULL`.

## 2. Backend and API tests with the coverage gate (Principle IV)

```bash
cd backend
uv run bash scripts/test.sh
uv run coverage report --fail-under=90
```

**Expected**: All tests pass, including the new ones:
- `tests/crud/test_category.py`
- `tests/api/routes/test_categories.py`
- category cases in `tests/api/routes/test_items.py`

Coverage is at least 90%.

## 3. Static checks and generated client (Principles I and III)

```bash
bash scripts/generate-client.sh    # regenerates frontend/src/client from OpenAPI
git status frontend/src/client     # changes present → commit them with the feature
uv run prek run --all-files        # ruff, mypy strict, ty, biome, typos
```

**Expected**:
- `CategoriesService` exists in `frontend/src/client`.
- `ItemPublic` has `category_id` and `category`.
- All hooks pass.

## 4. API smoke test via Swagger (`/docs`)

```bash
cd backend && uv run fastapi dev
```

Open <http://localhost:8000/docs>, authorize as the superuser from `.env`, then run these calls:

| # | Call | Expected |
|---|---|---|
| 1 | `POST /categories/` with `{"name": " Work "}` | 200, `name == "Work"` |
| 2 | `POST /categories/` with `{"name": "work"}` | 409 |
| 3 | `POST /items/` with `{"title": "A", "category_id": <Work id>}` | 200, `category.name == "Work"` |
| 4 | `PUT /items/{A}` with `{"category_id": null}` | 200, `category == null` |
| 5 | `PUT /items/{A}` with `{"category_id": <Work id>}`, then `DELETE /categories/{Work id}` | 200 each; `GET /items/{A}` shows `category == null` |
| 6 | `POST /items/` with `{"title": "B", "category_id": "<random uuid>"}` | 400 "Category not found" |

## 5. End-to-end tests (Principle IV)

```bash
docker compose build
docker compose run --rm backend bash scripts/prestart.sh
docker compose up -d --wait backend
bunx playwright test categories.spec.ts items.spec.ts
docker compose down -v
```

**Expected**: All specs pass. Together they cover:
- **US1**: create a category, assign it while adding an item, and see the Category column; also
  "No category".
- **US2**: clear the category on an item.
- **US3**: delete a category, then the affected items show "No category"; cancelling the delete
  keeps it.
- **Isolation**: a second user does not see the first user's categories.

## 6. Manual UI check (spec success criteria)

With the Compose stack running, sign in at <http://localhost:8000> as a fresh user:

1. Open **Categories** in the sidebar. Check the empty state, then add "Work".
   - Target: under 1 minute through step 2 (SC-001).
2. Go to **Items**, then **Add Item**. Choose Category "Work" and save. The row shows "Work".
3. Add an item without a category. The row shows "No category" (SC-002).
4. Edit the first item and set Category to "No category". The row shows "No category" (US2).
5. Assign "Work" again, then delete "Work" on Categories. The item remains and shows
   "No category" (SC-003).
6. Pre-existing items (created before the migration) show "No category" and remain editable
   (SC-004).
7. **Performance (SC-006)**: as one user, create 100 items assigned to categories. You can use
   `POST /items/` in `/docs`, or a short loop with `curl` and a token. Reload `/items` with the
   browser DevTools Network tab open. The page is fully rendered within 2 seconds, and the
   `GET /items/` request appears once (no per-row category requests).
8. **Admin view (spec edge cases)**: sign in as the superuser from `.env`.
   - On `/items`, the categorized items of the user from steps 1–5 show their category names.
   - Edit one of those items. The Category picker offers only "No category" and that item's
     current category.
   - Choosing "No category" and saving clears it.
