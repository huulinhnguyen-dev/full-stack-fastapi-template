# Contract: Categories API (new)

Base path: `/api/v1/categories`. Router file: `backend/app/api/routes/categories.py`, tag
`categories`. Every endpoint requires `Authorization: Bearer <token>` (`CurrentUser`). There is
**no superuser bypass**: every operation is scoped to the caller's own categories (research R8).

Schemas are defined in [../data-model.md](../data-model.md).

## Common errors

| Status | When | Body |
|---|---|---|
| `401` | No or invalid token | `{"detail": "Not authenticated"}` / `{"detail": "Could not validate credentials"}` (existing behavior) |
| `422` | Schema validation failure | FastAPI validation error list |

---

## `GET /api/v1/categories/`

List the caller's categories, ordered by `lower(name)` ascending.

**Query**: `skip: int = 0`, `limit: int = 100`

**200** → `CategoriesPublic`

```json
{
  "data": [
    {
      "id": "6f1c…",
      "name": "Personal",
      "owner_id": "a2b9…",
      "created_at": "2026-11-23T10:00:00Z"
    },
    {
      "id": "0d4e…",
      "name": "Work",
      "owner_id": "a2b9…",
      "created_at": "2026-11-23T10:01:00Z"
    }
  ],
  "count": 2
}
```

`count` is the caller's total number of categories, not the page size. Superusers also get only
their own categories.

---

## `POST /api/v1/categories/`

Create a category owned by the caller.

**Body**: `CategoryCreate`

```json
{ "name": "  Work  " }
```

**200** → `CategoryPublic`, with `name` trimmed to `"Work"`.

| Status | When | Body |
|---|---|---|
| `409` | Caller already has a category with this name (case-insensitive, trimmed) | `{"detail": "A category with this name already exists"}` |
| `422` | `name` missing, blank after trimming, or longer than 255 chars | validation error list |

---

## `DELETE /api/v1/categories/{id}`

Delete one of the caller's categories. Every item that referenced it gets `category_id = null`.
Items are never deleted.

**Path**: `id: UUID`

**200** → `Message`

```json
{ "message": "Category deleted successfully" }
```

| Status | When | Body |
|---|---|---|
| `404` | No category with this id | `{"detail": "Category not found"}` |
| `403` | Category belongs to another user (also for superusers) | `{"detail": "Not enough permissions"}` |

---

## Not provided (out of scope)

- `GET /categories/{id}` (no screen needs it)
- `PUT`/`PATCH /categories/{id}` (renaming is out of scope)
