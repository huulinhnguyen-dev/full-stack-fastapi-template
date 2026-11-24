# Contract: UI

This contract fixes the visible labels and roles that the Playwright tests in `frontend/tests/`
select on. Wording here is binding for tests.

## Sidebar

- New entry **"Categories"** (icon `Tag` from `lucide-react`), path `/categories`, visible to
  **every** signed-in user and placed after "Items".

## Categories page: `/categories`

Route file: `frontend/src/routes/_layout/categories.tsx`. Components live in
`frontend/src/components/Categories/`.

| Element | Contract |
|---|---|
| Heading | `h1` "Categories" with the subtitle "Create and manage your categories" |
| Add button | button "Add Category", which opens a dialog |
| Add dialog | title "Add Category"; field labelled **"Name"** (required); buttons "Cancel" and "Save" |
| Add success | toast "Category created successfully"; the new row appears in the table |
| Duplicate name | error toast with the backend detail "A category with this name already exists" |
| Blank name | inline message "Name is required"; no request sent |
| Table columns | **Name**, **Created**, Actions (screen-reader label "Actions") |
| Ordering | Alphabetical by name, ignoring case (as returned by the API) |
| Empty state | "You don't have any categories yet" with "Add a new category to get started" |
| Delete | the row's actions menu has "Delete Category", which opens a confirmation dialog |
| Delete dialog | text includes "Items using this category will become uncategorized."; buttons "Cancel" and "Delete" |
| Delete success | toast "Category deleted successfully"; row removed; items list refreshed |

## Items page: `/items` (changed)

| Element | Contract |
|---|---|
| Table columns | ID, Title, **Category** (new, after Title), Description, Actions |
| Category cell | category name; for none, the muted italic text **"No category"** (same style as "No description") |

## Add Item / Edit Item dialogs (changed)

| Element | Contract |
|---|---|
| Field | select labelled **"Category"**, below Description, optional |
| Options | "No category" first, then the user's categories in API order |
| Default | Add: "No category". Edit: the item's current category, or "No category" |
| No categories exist | select disabled, showing "No category". Helper text: "No categories yet. Create one on the Categories page." with a link to `/categories` |
| Editing an item owned by someone else (admin) | options limited to "No category" and the item's current category (research R8) |
| Submit | sends `category_id` (`null` for "No category") |
| Backend 400 "Category not found" (e.g. category deleted while the form was open) | error toast **"This category no longer exists. Please choose another."**; picker resets to "No category"; category list refreshed; dialog stays open |
| Other backend errors | existing `handleError` toast (backend `detail`) |

## Shared component

`frontend/src/components/Categories/CategorySelect.tsx` is used by both item dialogs. "No
category" maps to the sentinel `"none"` internally, which becomes `null` on submit (research R10).
