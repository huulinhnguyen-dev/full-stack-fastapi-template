---
description: "Task list for Item Categories"
---

# Tasks: Item Categories

**Input**: Design documents from `specs/001-item-category/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: REQUIRED. Constitution v2.0.0 Principle IV requires backend (CRUD) tests, API tests and
Playwright E2E tests for every feature. This overrides the template's "tests are optional" default.
Backend tests run against the real Postgres from Docker Compose, with no DB mocks.

**Organization**: Tasks are grouped by user story. Within each story, backend tasks come before
frontend tasks (Principle I: Backend First).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3, from [spec.md](./spec.md)
- Paths are relative to the repository root. Run backend commands from `backend/` with `uv run`.

## Conventions every task must follow

- Copy the structure of the existing Items code: `backend/app/api/routes/items.py`,
  `frontend/src/components/Items/*`, `backend/tests/api/routes/test_items.py` and
  `frontend/tests/items.spec.ts`.
- Error strings are binding (contracts): `"Category not found"`, `"Not enough permissions"`,
  `"A category with this name already exists"`, `"Category deleted successfully"`.
- UI labels are binding: see [contracts/ui.md](./contracts/ui.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm a green baseline before changing anything.

- [X] T001 Start services and verify the backend baseline:
  - Run `docker compose up -d db mailpit`.
  - In `backend/`, run `uv sync`, `uv run bash scripts/prestart.sh`, then `uv run alembic current`.
    It must print `fe56fa70289e (head)`.
  - Run `uv run bash scripts/test.sh` (backend/scripts/test.sh). All tests must pass.
- [X] T002 [P] Verify the frontend baseline. From the repo root, run `bun install`, then
  `bun run lint`. Both must pass without errors (frontend/package.json).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and wiring that every story depends on. All schema changes go into **one**
migration ([data-model.md](./data-model.md#migration)).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add the Category table model and the User relationship in `backend/app/models.py`.
  Place the new classes after the `UsersPublic` class and before `ItemBase`.
  - `CategoryBase(SQLModel)` with `name: str = Field(min_length=1, max_length=255)`.
  - `Category(CategoryBase, table=True)` with these fields:
    - `id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)`
    - `created_at: datetime | None = Field(default_factory=get_datetime_utc)`, the same
      definition as `Item.created_at`
    - `owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")`.
      There is no separate index here: the unique index below starts with `owner_id` and already
      serves owner lookups (research R2).
    - `owner: User | None = Relationship(back_populates="categories")`
  - Also on `Category`: `__table_args__ = (sqlalchemy.Index("uq_category_owner_id_lower_name",
    "owner_id", sqlalchemy.text("lower(name)"), unique=True),)`. Import `Index` and `text` from
    `sqlalchemy`. Unique per owner, case-insensitive (FR-003, research R2).
  - Add `categories: list[Category] = Relationship(back_populates="owner", cascade_delete=True)`
    to `User`, next to `items`.
  - Do **not** add a `Category.items` back-reference (research R4).
- [X] T004 Add the category column and relationship to the `Item` table model in
  `backend/app/models.py`. Depends on T003, same file.
  - `category_id: uuid.UUID | None = Field(default=None, foreign_key="category.id", nullable=True, ondelete="SET NULL", index=True)`
  - `category: Category | None = Relationship()`: one-way, no `back_populates`.
  - Do not change `ItemBase`, `ItemCreate`, `ItemUpdate` or `ItemPublic` in this task.
- [X] T005 Generate and hand-edit the migration in
  `backend/app/alembic/versions/<rev>_add_category_table_and_item_category_id.py`. Depends on T004.
  - Generate it with `uv run alembic revision --autogenerate -m "Add category table and item category_id"`.
  - Edit it so that:
    1. `down_revision = "fe56fa70289e"`.
    2. `upgrade()` runs, in order:
       - `op.create_table("category", …)` with columns:
         - `name` `sqlmodel.sql.sqltypes.AutoString(length=255)`, nullable=False
         - `id` `sa.Uuid()`, primary key
         - `created_at` `sa.DateTime(timezone=True)`, nullable=True, matching migration
           `fe56fa70289e`
         - `owner_id` `sa.Uuid()`, nullable=False
       - The named FK `sa.ForeignKeyConstraint(["owner_id"], ["user.id"], name="category_owner_id_fkey", ondelete="CASCADE")`.
       - `op.create_index("uq_category_owner_id_lower_name", "category", ["owner_id", sa.text("lower(name)")], unique=True)`.
       - `op.add_column("item", sa.Column("category_id", sa.Uuid(), nullable=True))`.
       - `op.create_foreign_key("item_category_id_fkey", "item", "category", ["category_id"], ["id"], ondelete="SET NULL")`.
       - `op.create_index("ix_item_category_id", "item", ["category_id"])`.
    3. `downgrade()` reverses `upgrade()` exactly, dropping by those explicit names. It must never
       call `drop_constraint(None, …)` (research R9).
  - Remove any unrelated operations that autogenerate emitted, and record each removal in the
    PR description.
- [X] T006 Verify the migration. Depends on T005.
  - In `backend/`, run `uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then
    `uv run alembic upgrade head`, then `uv run alembic check`.
  - All must succeed. Follow the note in [quickstart.md](./quickstart.md) §1 about the functional
    index and `alembic check`.
- [X] T007 [P] Update the test teardown in `backend/tests/conftest.py`.
  - Import `Category` from `app.models`.
  - In the session-scoped `db` fixture, add `session.execute(delete(Category))` after the
    `delete(Item)` statement and before `delete(User)` (research R11).
- [X] T008 [P] Create and register the categories router.
  - Create `backend/app/api/routes/categories.py` with
    `router = APIRouter(prefix="/categories", tags=["categories"])` and no endpoints yet.
  - Add `categories` to the import in `backend/app/api/main.py` and register it with
    `api_router.include_router(categories.router)` after `items.router`.

**Checkpoint**: The migration applies and reverts cleanly, the existing test suite still passes
(`uv run bash scripts/test.sh`), and `/docs` shows an empty `categories` tag.

---

## Phase 3: User Story 1 - Categorize an item and see it in the list (Priority: P1) 🎯 MVP

**Goal**:
- Users create personal categories on a Categories page.
- They can pick one while adding or editing an item.
- The Items list shows a Category column, with "No category" when none is set.

**Independent Test**:
- Sign in, create "Work" on the Categories page, then add an item with "Work". Its row shows
  "Work".
- Add an item without a category. Its row shows "No category".
- A second user does not see "Work".

### Backend: schemas and data access for US1

- [X] T009 [US1] Add the category and item schemas in `backend/app/models.py`.
  - `CategoryCreate(CategoryBase)` with `@field_validator("name", mode="before")`. It returns
    `value.strip()` when `value` is a `str` and otherwise returns `value` unchanged, so `"   "`
    then fails `min_length=1` with 422 (research R3). Import `field_validator` from `pydantic`.
  - `CategoryPublic(CategoryBase)` with `id: uuid.UUID`, `owner_id: uuid.UUID`,
    `created_at: datetime | None = None`.
  - `CategoriesPublic(SQLModel)` with `data: list[CategoryPublic]` and `count: int`.
  - `ItemCreate`: add `category_id: uuid.UUID | None = None`.
  - `ItemUpdate`: add `category_id: uuid.UUID | None = None`.
  - `ItemPublic`: add `category_id: uuid.UUID | None = None` and
    `category: CategoryPublic | None = None`.
  - Field details are in [data-model.md](./data-model.md#schemas-pydantic--sqlmodel-non-table).
- [X] T010 [US1] Add category data-access functions to `backend/app/crud.py`, keyword-only like
  the existing functions.
  - `create_category(*, session: Session, category_in: CategoryCreate, owner_id: uuid.UUID) -> Category`
    uses `Category.model_validate(category_in, update={"owner_id": owner_id})`, then add, commit
    and refresh.
  - `get_category_by_name(*, session: Session, owner_id: uuid.UUID, name: str) -> Category | None`
    selects where `Category.owner_id == owner_id` and
    `func.lower(Category.name) == name.strip().lower()`.
  - Import `func` from `sqlmodel`.
  - `create_item` needs no change, because `model_validate` already copies `category_id`.
- [X] T011 [US1] Create the test helper `backend/tests/utils/category.py`, modeled on
  `backend/tests/utils/item.py`.
  - `create_random_category(db: Session, *, owner_id: uuid.UUID | None = None, name: str | None = None) -> Category`
  - It creates a random user via `create_random_user(db)` when `owner_id` is None.
  - It uses `random_lower_string()` when `name` is None, then calls `crud.create_category`.

### Tests for User Story 1 (write first; they must fail until T015–T016)

- [X] T012 [P] [US1] Backend tests in `backend/tests/crud/test_category.py`:
  - `crud.create_category` stores the trimmed name and the owner.
  - `CategoryCreate(name="  Work  ").name == "Work"`.
  - `CategoryCreate(name="   ")` and `CategoryCreate(name="x"*256)` raise `pydantic.ValidationError`.
  - `crud.get_category_by_name` matches case-insensitively, e.g. "WORK" finds "Work".
  - `crud.get_category_by_name` returns None for the same name under a different owner.
  - Two different owners can each create "Work".
  - Inserting a duplicate `Category(name="work", owner_id=<same>)` directly, bypassing the
    pre-check, raises `sqlalchemy.exc.IntegrityError` on commit. Call `db.rollback()` afterwards.
- [X] T013 [P] [US1] API tests for list and create in `backend/tests/api/routes/test_categories.py`,
  using the `client`, `superuser_token_headers`, `normal_user_token_headers` and `db` fixtures.
  - `POST /api/v1/categories/` with `{"name": "  <random>  "}` returns 200 with the trimmed
    `name`, plus `id`, `owner_id` and `created_at`.
  - The same name in different case returns 409 `{"detail": "A category with this name already exists"}`.
  - `{"name": "   "}` returns 422; a name of 256 chars returns 422; a missing `name` returns 422.
  - No `Authorization` header returns 401 on **both** `GET /api/v1/categories/` and
    `POST /api/v1/categories/` (constitution Principle IV).
  - `GET /api/v1/categories/?skip=abc` returns 422.
  - `GET /api/v1/categories/` returns only the caller's categories, ordered case-insensitively
    by name (create "b", "A", "c", expect A, b, c), with `count` equal to the caller's total.
  - The superuser's `GET` does **not** include a normal user's categories.
- [X] T014 [P] [US1] Item/category API tests, appended to `backend/tests/api/routes/test_items.py`:
  - `POST /items/` with the caller's `category_id` returns 200, with `category_id` set and
    `category.name` equal to the category name.
  - `POST /items/` without `category_id` returns 200 with `category_id` and `category` both null.
  - `POST /items/` with `category_id=str(uuid.uuid4())` returns 400 `{"detail": "Category not found"}`.
  - `POST /items/` using another user's category returns 400 `"Category not found"`.
  - `PUT /items/{id}` setting a category, then changing it to a second category, returns 200
    with `category.name` updated.
  - `PUT /items/{id}` using another user's category returns 400, and a follow-up `GET` shows the
    item unchanged.
  - The superuser runs `PUT` on a normal user's item with the **superuser's own** category and
    gets 400 (research R8).
  - `GET /items/` returns the `category` object for categorized items.
  - `GET /items/{id}` for an item created without a category returns `category_id` null.
  - The superuser's `GET /items/` includes a **normal user's** categorized item, with
    `category.name` set (spec edge case "Administrator viewing all items").
  - Missing login (constitution Principle IV): no `Authorization` header returns 401 on
    `POST /items/`, `PUT /items/{id}`, `GET /items/` and `GET /items/{id}`.
  - Invalid input (constitution Principle IV): `{"title": "A", "category_id": "not-a-uuid"}`
    returns 422 on `POST /items/`, and `{"category_id": "not-a-uuid"}` returns 422 on
    `PUT /items/{id}`. After the PUT, a `GET` shows the item unchanged.
  - Added during implementation (analysis finding C3): `GET /items/?skip=abc` and
    `GET /items/not-a-uuid` return 422.

### Backend implementation for User Story 1

- [X] T015 [US1] Implement list and create in `backend/app/api/routes/categories.py`. Depends on
  T009 and T010; contract in [contracts/categories-api.md](./contracts/categories-api.md).
  - `@router.get("/", response_model=CategoriesPublic) def read_categories(session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100)`
    - `count` comes from `select(func.count()).select_from(Category).where(Category.owner_id == current_user.id)`.
    - The rows come from `select(Category).where(Category.owner_id == current_user.id).order_by(func.lower(Category.name)).offset(skip).limit(limit)`.
    - It returns `CategoriesPublic(data=[CategoryPublic.model_validate(c) for c in rows], count=count)`.
    - There is **no** superuser branch.
  - `@router.post("/", response_model=CategoryPublic) def create_category(*, session: SessionDep, current_user: CurrentUser, category_in: CategoryCreate)`
    - If `crud.get_category_by_name(...)` finds a match, raise
      `HTTPException(status_code=409, detail="A category with this name already exists")`.
    - Otherwise call `crud.create_category`.
    - Wrap the creation in `try/except IntegrityError` that calls `session.rollback()` and raises
      the same 409 (research R2).
  - Docstrings follow the items router style (`"""Retrieve categories."""`, `"""Create new category."""`).
- [X] T016 [US1] Add category support to `backend/app/api/routes/items.py`. Depends on T009.
  - Add a module-level helper,
    `def ensure_category_for_owner(session: Session, category_id: uuid.UUID, owner_id: uuid.UUID) -> None`.
    It runs `session.get(Category, category_id)` and raises
    `HTTPException(status_code=400, detail="Category not found")` when the result is None or
    `category.owner_id != owner_id` (research R6).
  - `create_item`: if `item_in.category_id is not None`, call
    `ensure_category_for_owner(session, item_in.category_id, current_user.id)` before creating.
  - `update_item`: after the existing 404 and 403 checks, if
    `update_dict.get("category_id") is not None`, call
    `ensure_category_for_owner(session, update_dict["category_id"], item.owner_id)`. Validate
    against the **item's** owner, not the current user.
    - An explicit `null` skips validation and clears the category. A missing key leaves it
      unchanged, because `exclude_unset=True` is already used (research R7).
  - `read_items`: add `.options(selectinload(Item.category))` to both the superuser and owner
    `select(Item)` statements. Import `selectinload` from `sqlalchemy.orm`.
  - Leave the response handling as it is: `ItemPublic.model_validate(item)` and `return item`
    serialize the nested `category`.
- [X] T017 [US1] Run the backend suite and coverage. In `backend/`, run
  `uv run bash scripts/test.sh`, then `uv run coverage report --fail-under=90`. T012–T014 pass
  and coverage is ≥90% (backend/scripts/test.sh).
- [X] T018 [US1] Regenerate the frontend client.
  - From the repo root, run `bash scripts/generate-client.sh`.
  - Confirm `frontend/src/client/` contains a `CategoriesService` with `readCategories` and
    `createCategory`, and that `ItemPublic` has `category_id` and `category`.
  - Do not edit the generated files by hand (Principle I).

### Frontend implementation for User Story 1

- [X] T019 [P] [US1] Create `frontend/src/components/Categories/columns.tsx`, modeled on
  `frontend/src/components/Items/columns.tsx`.
  - `columns: ColumnDef<DataTableFeatures, CategoryPublic>[]` with a **Name** column
    (`font-medium`) and a **Created** column. Created shows
    `new Date(created_at).toLocaleDateString()`, or "—" when null.
  - No actions column yet; US3 adds it in T036.
- [X] T020 [P] [US1] Create `frontend/src/components/Categories/AddCategory.tsx`, modeled on
  `frontend/src/components/Items/AddItem.tsx`.
  - Button "Add Category" with the `Plus` icon; dialog title "Add Category"; description
    "Fill in the details to add a new category."
  - One field labelled "Name" (required asterisk), with zod
    `name: z.string().trim().min(1, { message: "Name is required" }).max(255, { message: "Name must be at most 255 characters" })`
    (the `max` message was added during implementation, analysis finding U3).
  - The mutation calls `CategoriesService.createCategory({ body: data })`.
    - On success: toast "Category created successfully", reset the form and close the dialog.
    - On error: `handleError.bind(showErrorToast)`.
    - On settled: invalidate `{ queryKey: ["categories"] }`.
- [X] T021 [P] [US1] Create `frontend/src/components/Pending/PendingCategories.tsx`, a skeleton
  table copied from `frontend/src/components/Pending/PendingItems.tsx` with Name and Created
  column headers.
- [X] T022 [US1] Create the Categories page route `frontend/src/routes/_layout/categories.tsx`,
  modeled on `frontend/src/routes/_layout/items.tsx`. Depends on T019–T021.
  - `getCategoriesQueryOptions()` uses
    `queryFn: async () => (await CategoriesService.readCategories({ query: { skip: 0, limit: 100 } })).data`
    and `queryKey: ["categories"]`.
  - Head title "Categories - FastAPI Template".
  - `h1` "Categories", subtitle "Create and manage your categories", and `<AddCategory />` in
    the header.
  - Empty state: "You don't have any categories yet" / "Add a new category to get started".
  - Otherwise render `<DataTable columns={columns} data={categories.data} />`, wrapped in
    `Suspense` with `PendingCategories`.
  - Run `bun run --filter frontend build` (or the dev server) so `frontend/src/routeTree.gen.ts`
    is regenerated, and commit it.
- [X] T023 [P] [US1] Add the sidebar entry in `frontend/src/components/Sidebar/AppSidebar.tsx`.
  - Import `Tag` from `lucide-react`.
  - Add `{ icon: Tag, title: "Categories", path: "/categories" }` to `baseItems` directly after
    the Items entry, so every signed-in user sees it.
- [X] T024 [P] [US1] Create the shared picker `frontend/src/components/Categories/CategorySelect.tsx`
  (research R10, [contracts/ui.md](./contracts/ui.md#add-item--edit-item-dialogs-changed)).
  - Props:
    `{ value: string | null; onChange: (value: string | null) => void; currentCategory?: CategoryPublic | null; ownedByCurrentUser?: boolean (default true); disabled?: boolean }`.
  - Use the shadcn `Select` from `@/components/ui/select`. The sentinel value `"none"` maps to
    `null` in both directions, and the option label is "No category".
  - When `ownedByCurrentUser` is true, load options with
    `useQuery({ queryKey: ["categories"], queryFn: … readCategories({ query: { skip: 0, limit: 100 } }) })`
    and list them after "No category".
  - When it is false, the options are only "No category" plus `currentCategory`, if present,
    and no query is made.
  - When the user owns the item and has zero categories:
    - render the select disabled, showing "No category";
    - add the helper text "No categories yet. Create one on the Categories page.";
    - make "Categories page" a TanStack Router `<Link to="/categories">`.
  - Also export two helpers for the item dialogs (spec edge case "Category deleted while an item
    form is open"):
    - `STALE_CATEGORY_MESSAGE = "This category no longer exists. Please choose another."`
    - `isStaleCategoryError(err: Error): boolean`, which returns true when `err` is an
      `AxiosError` with `response.status === 400` and `response.data.detail === "Category not found"`.
- [X] T025 [US1] Add the Category field to `frontend/src/components/Items/AddItem.tsx`. Depends
  on T018 and T024.
  - Extend `formSchema` with `category_id: z.string().nullable()` and default values with
    `category_id: null`.
  - Below Description, add a `FormField` named `category_id` with `FormLabel` "Category",
    rendering `<CategorySelect value={field.value} onChange={field.onChange} />`.
  - `onSubmit` passes `category_id` in the `ItemCreate` body.
  - In the mutation's `onError`, if `isStaleCategoryError(err)`:
    - call `showErrorToast(STALE_CATEGORY_MESSAGE)`;
    - run `form.setValue("category_id", null)`;
    - invalidate `{ queryKey: ["categories"] }`;
    - keep the dialog open.

    Otherwise fall back to `handleError.call(showErrorToast, err)`.
- [X] T026 [US1] Add the Category field to `frontend/src/components/Items/EditItem.tsx`. Depends
  on T018 and T024.
  - Extend `formSchema` with `category_id: z.string().nullable()` and default to
    `item.category_id ?? null`.
  - Get `user` from `useAuth()` (`@/hooks/useAuth`) and pass
    `ownedByCurrentUser={item.owner_id === user?.id}` and `currentCategory={item.category}` to
    `CategorySelect` (research R8).
  - The mutation body **always** includes `category_id`, as `null` when "No category" is chosen
    (research R7).
  - Use the same stale-category `onError` handling as T025.
- [X] T027 [P] [US1] Add the Category column in `frontend/src/components/Items/columns.tsx`.
  - Insert `{ id: "category", header: "Category", cell: … }` between the Title and Description
    columns.
  - The cell shows `row.original.category?.name`. When there is none, it shows "No category"
    with the same classes as "No description" (`text-muted-foreground`, plus `italic` when
    empty).
- [X] T028 [P] [US1] Add `randomCategoryName = () => \`Category ${Math.random().toString(36).substring(7)}\``
  to `frontend/tests/utils/random.ts`, following the `randomItemTitle` pattern.

### E2E tests for User Story 1

- [X] T029 [US1] Create `frontend/tests/categories.spec.ts`, structured like
  `frontend/tests/items.spec.ts`: a fresh user via `createUser`, then `logInUser`, then
  `page.goto("/categories")`. Depends on T022, T023 and T028. Tests:
  - The page shows the heading "Categories" and the "Add Category" button.
  - The sidebar link "Categories" navigates to `/categories`.
  - Create a category: the toast "Category created successfully" appears, the name is visible
    in the table, and the empty state is gone.
  - Duplicate name in different case: the toast "A category with this name already exists"
    appears.
  - Blank name shows "Name is required".
  - Isolation: user A creates a category. User B, in a new `browser.newContext()`, logs in, opens
    `/categories` and does not see A's category name.
- [X] T030 [US1] Add category assignment tests to the "Items management" describe in
  `frontend/tests/items.spec.ts`. Depends on T025–T028. Tests:
  - Create a category on `/categories`, go to `/items`, and click "Add Item". Fill Title, choose
    Category, then Save. The row shows the category name.
  - Create an item without choosing a category. Its row shows "No category".
  - Edit an existing uncategorized item and choose a category. The row shows the category name.
  - With a fresh user that has no categories, open "Add Item". The Category select is disabled
    and the text "No categories yet" is visible.

**Checkpoint**: US1 is fully functional. Backend tests (T012–T014) and E2E tests (T029–T030) pass.
This is the MVP.

---

## Phase 4: User Story 2 - Remove the category from an item (Priority: P2)

**Goal**: A user clears an item's category. The item remains, shows "No category", and the
category still exists.

**Independent Test**: Assign "Work" to two items, clear it on one, and confirm that item shows
"No category" while the other still shows "Work" and "Work" is still selectable.

**Note**: The backend behavior is already delivered by T016's explicit-null handling (research
R7), and the UI sends `null` from T026. This phase locks the behavior in with tests and fixes
anything they expose.

### Tests for User Story 2

- [X] T031 [P] [US2] Clear-category API tests, appended to `backend/tests/api/routes/test_items.py`:
  - `PUT /items/{id}` with `{"category_id": null}` on a categorized item returns 200 with
    `category_id` and `category` both null.
  - `PUT /items/{id}` with only `{"title": "new"}` on a categorized item returns 200 with the
    category **unchanged**.
  - Two items share one category. Clearing it on the first leaves the second's `category_id`
    unchanged (check with `GET /items/{second}`), and the category still appears in
    `GET /categories/`.
  - The superuser clears the category on a normal user's item and gets 200 (research R8).
- [X] T032 [P] [US2] Clear-category E2E test in the "Items management" describe of
  `frontend/tests/items.spec.ts`.
  - Create a category and two items assigned to it.
  - Edit the first item and select "No category", then Save. The toast "Item updated
    successfully" appears and that row shows "No category".
  - The second row still shows the category name.

### Implementation for User Story 2

- [X] T033 [US2] Run `uv run bash scripts/test.sh` in `backend/` and
  `bunx playwright test items.spec.ts`, which needs the Compose stack running; see
  [quickstart.md](./quickstart.md) §5.
  - If T031 or T032 fail, fix the cause in `backend/app/api/routes/items.py` (`update_item`) or
    `frontend/src/components/Items/EditItem.tsx`.
  - Typical causes are a dropped null value or validation run on `None`.

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Delete a category (Priority: P3)

**Goal**:
- A user deletes a category from the Categories page after confirming.
- Items that used it remain and show "No category".
- Cancelling changes nothing.

**Independent Test**: Assign a category to two items, then delete it. Both items still exist and
show "No category", and the category is no longer selectable.

### Tests for User Story 3 (write first)

- [X] T034 [P] [US3] Backend tests for delete behavior, appended to
  `backend/tests/crud/test_category.py`:
  - Create a category and an item with `category_id` set. Run `db.delete(category)`,
    `db.commit()`, then `db.refresh(item)`. The item still exists and `item.category_id is None`
    (DB `ON DELETE SET NULL`, research R4).
  - Create a user with a category. Run `db.delete(user)` and `db.commit()`. Then
    `db.get(Category, category_id)` is None (account deletion edge case).
- [X] T035 [P] [US3] API tests for delete, appended to
  `backend/tests/api/routes/test_categories.py`:
  - The owner calls `DELETE /api/v1/categories/{id}` and gets 200
    `{"message": "Category deleted successfully"}`. A follow-up `GET /categories/` no longer
    lists it.
  - Deleting a category used by two items returns 200. `GET /items/{id}` for both returns
    `category_id` null, and both items still exist.
  - A random UUID returns 404 `{"detail": "Category not found"}`.
  - A normal user deleting another user's category gets 403 `{"detail": "Not enough permissions"}`.
  - The **superuser** deleting a normal user's category also gets 403 (no bypass, research R8).
  - No `Authorization` header returns 401.
  - Added during implementation (analysis finding C3): `DELETE /api/v1/categories/not-a-uuid`
    returns 422.

### Backend implementation for User Story 3

- [X] T036 [US3] Implement delete in `backend/app/api/routes/categories.py`
  ([contracts/categories-api.md](./contracts/categories-api.md#delete-apiv1categoriesid)):
  - `@router.delete("/{id}", response_model=Message) def delete_category(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Message`
  - `category = session.get(Category, id)`. If it is None, raise 404 "Category not found".
  - If `category.owner_id != current_user.id`, raise 403 "Not enough permissions". There is
    **no** `is_superuser` exception.
  - Otherwise `session.delete(category)`, `session.commit()`, and return
    `Message(message="Category deleted successfully")`.
  - The database sets `item.category_id` to NULL; there is no ORM-side update.
- [X] T037 [US3] Run `uv run bash scripts/test.sh` in `backend/`. T034 and T035 pass. Then run
  `bash scripts/generate-client.sh` from the repo root and confirm
  `CategoriesService.deleteCategory` exists in `frontend/src/client/`.

### Frontend implementation for User Story 3

- [X] T038 [P] [US3] Create `frontend/src/components/Categories/DeleteCategory.tsx`, modeled on
  `frontend/src/components/Items/DeleteItem.tsx`. Props: `{ id: string; onSuccess: () => void }`.
  - A `DropdownMenuItem` (`variant="destructive"`, `Trash2` icon) labelled "Delete Category"
    opens a dialog titled "Delete Category".
  - Dialog description: "This category will be permanently deleted. Items using this category
    will become uncategorized."
  - Buttons: "Cancel", and a `LoadingButton` labelled "Delete" with `variant="destructive"`.
  - The mutation calls `CategoriesService.deleteCategory({ path: { id } })`.
    - On success: toast "Category deleted successfully".
    - On settled: invalidate `{ queryKey: ["categories"] }` **and** `{ queryKey: ["items"] }`.
- [X] T039 [US3] Create `frontend/src/components/Categories/CategoryActionsMenu.tsx`, modeled on
  `frontend/src/components/Items/ItemActionsMenu.tsx`, rendering only
  `<DeleteCategory id={category.id} onSuccess={() => setOpen(false)} />`. Then add the actions
  column to `frontend/src/components/Categories/columns.tsx`:
  - `{ id: "actions", header: () => <span className="sr-only">Actions</span>, cell: … }`
  - The cell is `<div className="flex justify-end"><CategoryActionsMenu category={row.original} /></div>`.

### E2E tests for User Story 3

- [X] T040 [US3] Add delete tests to `frontend/tests/categories.spec.ts`:
  - Delete an unused category: open the row's actions menu and click "Delete Category", then
    "Delete". The toast "Category deleted successfully" appears and the row is gone.
  - Delete a category that is in use:
    - Create a category and an item assigned to it on `/items`.
    - Delete the category on `/categories`.
    - On `/items`, the item still exists and shows "No category".
    - In "Add Item", the deleted category is not among the Category options.
  - Cancel: open the delete dialog and click "Cancel". The category row is still visible.
  - Category deleted while the item form is open:
    1. Create a category. On `/items`, open "Add Item", fill Title and choose that category.
    2. In a second tab (`const other = await page.context().newPage()`), delete the category on
       `/categories`.
    3. Back in the first tab, click "Save". The toast "This category no longer exists. Please
       choose another." appears and the dialog is still open.

**Checkpoint**: All three user stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T041 Run all quality hooks with `uv run prek run --all-files` from the repo root
  (.pre-commit-config.yaml). Fix every ruff, mypy (strict), ty, Biome or typos finding in the
  changed files.
- [X] T042 Run the full backend gate in `backend/`: `uv run bash scripts/test.sh` and
  `uv run coverage report --fail-under=90`. Add tests for any uncovered branch in
  `backend/app/api/routes/categories.py` or `backend/app/api/routes/items.py`, such as the
  `IntegrityError` 409 path.
- [X] T043 Run the full E2E suite per [quickstart.md](./quickstart.md) §5 (frontend/tests/). The
  existing specs in `frontend/tests/items.spec.ts` and `frontend/tests/admin.spec.ts` must still
  pass.
- [X] T044 Validate the feature end to end against [quickstart.md](./quickstart.md):
  - §1: migration round-trip.
  - §4: the Swagger smoke table.
  - §6: the manual UI steps, including SC-001 (under 1 minute), SC-004 (pre-existing items
    show "No category"), SC-006 (100 categorized items render within 2 seconds), and the admin
    category picker check.
- [X] T045 [P] Add a release note to `release-notes.md` under `## Latest Changes`, in a
  `### Features` subsection (create it above `### Fixes` if missing), following the existing
  bullet format. Example: `* ✨ Add personal item categories with a Categories page and a
  Category column in the Items list.`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on Setup and blocks all stories. Order: T003 → T004 → T005
  → T006. T007 and T008 can run in parallel after T003.
- **US1 (Phase 3)**: depends on Phase 2.
- **US2 (Phase 4)**: depends on US1's T016 (backend) and T026 (EditItem field). Its tests are
  independent of US3.
- **US3 (Phase 5)**: depends on Phase 2 and on US1's T015 (the router exists) and T022 (the
  Categories page exists). It is independent of US2.
- **Polish (Phase 6)**: depends on every story you intend to ship.

### Within each story (Principle I)

Order: schemas and CRUD → test helper → backend and API tests (failing) → routes → backend suite
green → client regeneration → frontend components → E2E tests.

### Task dependency summary

| Task | Depends on |
|---|---|
| T009 | T004 |
| T010 | T009 |
| T011 | T010 |
| T012–T014 | T011 |
| T015 | T010 |
| T016 | T009 |
| T017 | T012–T016 |
| T018 | T017 |
| T019, T020, T024 | T018 |
| T021, T023, T028 | Phase 2 (they don't use the client) |
| T022 | T019–T021 |
| T025, T026 | T024 |
| T027 | T018 |
| T029 | T022, T023, T028 |
| T030 | T025–T028 |
| T031 | T014, T016 (same test file as T014) |
| T032 | T026, T030 (same spec file as T030) |
| T033 | T031, T032 |
| T034 | T012 (same test file) |
| T035 | T013, T015 (same test file as T013) |
| T036 | T034, T035 |
| T037 | T036 |
| T038 | T037 |
| T039 | T038 |
| T040 | T029, T039 (same spec file as T029) |
| T041–T045 | all stories |

---

## Parallel Examples

### Phase 2

```text
After T003: T007 (tests/conftest.py) ∥ T008 (routes/categories.py + api/main.py)
```

### User Story 1

```text
Tests, after T011:
  T012 (tests/crud/test_category.py)
  ∥ T013 (tests/api/routes/test_categories.py)
  ∥ T014 (tests/api/routes/test_items.py)

Backend, after T009 and T010:
  T015 (routes/categories.py) ∥ T016 (routes/items.py)

Frontend, after T018:
  T019 (Categories/columns.tsx)
  ∥ T020 (Categories/AddCategory.tsx)
  ∥ T021 (Pending/PendingCategories.tsx)
  ∥ T023 (Sidebar/AppSidebar.tsx)
  ∥ T024 (Categories/CategorySelect.tsx)
  ∥ T027 (Items/columns.tsx)
  ∥ T028 (tests/utils/random.ts)
```

### User Story 2

```text
T031 (tests/api/routes/test_items.py) ∥ T032 (frontend/tests/items.spec.ts)
```

### User Story 3

```text
T034 (tests/crud/test_category.py) ∥ T035 (tests/api/routes/test_categories.py)
T038 (Categories/DeleteCategory.tsx) can start once T037 has regenerated the client
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1, Setup: T001–T002.
2. Phase 2, Foundational: T003–T008. Migration verified.
3. Phase 3, US1: T009–T030.
4. **Stop and validate**: run quickstart §2, §3 and §5 for US1. Users can now categorize items and
   see the column.

### Incremental delivery

1. MVP (US1), then demo.
2. Add US2 (T031–T033, mostly tests, since the behavior arrived with US1), then demo.
3. Add US3 (T034–T040), then demo.
4. Polish (T041–T045), then open the PR against `master`.

### Notes

- Commit after each checkpoint at minimum. Every commit must pass `prek`.
- Never edit `frontend/src/client/` or `frontend/src/routeTree.gen.ts` by hand; regenerate them.
- If a test passes before its implementation task, the test is not testing the new behavior.
  Tighten it.
