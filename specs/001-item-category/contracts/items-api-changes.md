# Contract: Items API changes

Router file: `backend/app/api/routes/items.py`. Authentication, ownership, and superuser rules
are unchanged except where noted. Every change is **additive**; clients that don't send
`category_id` behave exactly as before (FR-013).

## Response shape: `ItemPublic`

Two fields are added:

```json
{
  "id": "9e3a…",
  "title": "Quarterly report",
  "description": "Draft",
  "owner_id": "a2b9…",
  "created_at": "2026-11-23T10:05:00Z",
  "category_id": "0d4e…",
  "category": {
    "id": "0d4e…",
    "name": "Work",
    "owner_id": "a2b9…",
    "created_at": "2026-11-23T10:01:00Z"
  }
}
```

An uncategorized item has `"category_id": null, "category": null`.

This applies to `GET /items/`, `GET /items/{id}`, `POST /items/` and `PUT /items/{id}`. The list
endpoint eager-loads categories (research R5).

## `POST /api/v1/items/`

**Body**: `ItemCreate` gains an optional `category_id`.

```json
{ "title": "Quarterly report", "description": "Draft", "category_id": "0d4e…" }
```

Omitting `category_id` or sending `null` creates an uncategorized item.

| New status | When | Body |
|---|---|---|
| `400` | `category_id` doesn't exist, or belongs to a user other than the new item's owner | `{"detail": "Category not found"}` |

## `PUT /api/v1/items/{id}`

**Body**: `ItemUpdate` gains an optional `category_id`. Partial-update semantics are unchanged
(research R7):

| Request body contains | Effect |
|---|---|
| `"category_id": "<uuid>"` | Set or change category |
| `"category_id": null` | Clear category (item becomes uncategorized) |
| no `category_id` key | Category unchanged |

| New status | When | Body |
|---|---|---|
| `400` | `category_id` doesn't exist, or its owner ≠ **the item's owner** (applies to superusers editing other users' items too) | `{"detail": "Category not found"}` |

The order of checks is unchanged: `404 Item not found`, then `403 Not enough permissions`, then
the new `400 Category not found`. On any error the item is unchanged.

## `GET /api/v1/items/`, `GET /api/v1/items/{id}`, `DELETE /api/v1/items/{id}`

These endpoints have no request changes. The two GETs return the extended `ItemPublic`.

## Generated client

After these changes, run `bash scripts/generate-client.sh` and commit the regenerated
`frontend/src/client/` (constitution Principle I).
