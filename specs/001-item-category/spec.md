# Feature Specification: Item Categories

**Feature Branch**: `feat/add-category-to-item`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "User can add the category for the item, and the category column should be show in list, category should store in the DB, create a table Category in database, user also can remove the category, category is optional"

## Clarifications

### Session 2026-11-23

- Q: Are categories private to each user, or shared? → A: Private. Each user has their own
  categories, the same way items are owned today.
- Q: Where are categories created and deleted? → A: On a dedicated Categories page in the main
  navigation. The item add/edit form only offers a choice among existing categories.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Categorize an item and see it in the list (Priority: P1)

A signed-in user opens the Categories page and creates a category (for example "Work"). They then
assign it to an item, either while adding a new item or by editing an existing one. On the Items page, a new **Category** column
shows each item's category name, or a clear "no category" indicator when none is set.

**Why this priority**: This is the core value of the feature. Without creating, assigning, and
seeing categories, nothing else in the feature is useful.

**Independent Test**: Sign in, create a category on the Categories page, add an item with that category, and confirm the
Items list shows the category name in the Category column. Add a second item without a category
and confirm it shows the "no category" indicator.

**Acceptance Scenarios**:

1. **Given** a signed-in user with no categories, **When** they create a category named "Work"
   on the Categories page, **Then** "Work" appears in their category list and becomes available
   to choose when adding or editing an item.
2. **Given** the category "Work" exists, **When** the user adds a new item and selects "Work",
   **Then** the item is saved and the Items list shows "Work" in that item's Category column.
3. **Given** the category "Work" exists, **When** the user adds a new item without selecting a
   category, **Then** the item is saved successfully and its Category column shows the
   "no category" indicator.
4. **Given** an existing item with no category, **When** the user edits it and selects "Work",
   **Then** the Items list shows "Work" for that item.
5. **Given** an item with category "Work" and a category "Personal" exists, **When** the user
   edits the item and selects "Personal", **Then** the Items list shows "Personal" for that item.
6. **Given** the user already has a category named "Work", **When** they try to create another
   category named "work", **Then** creation is rejected with a message that the name is taken.
7. **Given** user A has a category "Work", **When** user B opens their Categories page or the
   item form, **Then** user A's "Work" is not shown, and user B can create their own "Work".

---

### User Story 2 - Remove the category from an item (Priority: P2)

A user who no longer wants an item categorized edits the item and clears its category. The item
remains, and it shows as uncategorized in the list.

**Why this priority**: The description states that category is optional and that users can remove
it. Users need a way to undo an assignment without deleting the item or the category.

**Independent Test**: Assign a category to an item, then edit the item and clear the category.
Confirm the item still exists, the Category column shows the "no category" indicator, and the
category itself still exists for other items.

**Acceptance Scenarios**:

1. **Given** an item with category "Work", **When** the user edits the item and clears the
   category, **Then** the item is saved and its Category column shows the "no category" indicator.
2. **Given** two items both in "Work", **When** the user clears the category on one of them,
   **Then** the other item still shows "Work" and "Work" remains available for selection.

---

### User Story 3 - Delete a category (Priority: P3)

A user deletes a category they no longer need from the Categories page. Before deletion they are asked to confirm and told
that items using it will become uncategorized. After deletion, those items remain and show as
uncategorized; the category is no longer offered for selection.

**Why this priority**: Keeps the category list tidy over time. Useful, but the feature delivers
value without it.

**Independent Test**: Create a category, assign it to two items, delete the category, and confirm
both items still exist and show the "no category" indicator, and the category no longer appears
as a choice.

**Acceptance Scenarios**:

1. **Given** a category "Old" that no item uses, **When** the user deletes it and confirms,
   **Then** "Old" is no longer offered when adding or editing items.
2. **Given** a category "Work" used by two items, **When** the user deletes it and confirms,
   **Then** both items still exist and show the "no category" indicator.
3. **Given** the user starts deleting a category, **When** they cancel the confirmation,
   **Then** the category and its item assignments are unchanged.

---

### Edge Cases

- **Blank or whitespace-only name**: Creating a category with an empty or whitespace-only name is
  rejected with a clear message.
- **Over-long name**: A name longer than 255 characters is rejected with a clear message.
- **Duplicate name, different case or surrounding spaces**: " work " and "Work" are treated as the
  same name; the second is rejected.
- **Category deleted while an item form is open**: If the user saves an item with a category that
  was deleted in the meantime, the save is rejected with a message asking them to choose again;
  no partial change is saved.
- **Assigning another user's category**: Any attempt to assign a category that belongs to someone
  other than the item's owner is rejected and the item is unchanged (see FR-011).
- **Deleting another user's category**: A user cannot view or delete another user's categories.
  This applies to administrators too, since categories are personal.
- **Existing items before this feature**: All items created before the feature launches appear
  in the list as uncategorized and remain fully editable.
- **No categories at all**: The item add/edit form still works. The category choice says no
  categories exist yet and points the user to the Categories page. Items save without one.
- **Account deletion**: When a user account is deleted, categories it owns are removed along with
  its items.
- **Administrator viewing all items**: An administrator who sees other users' items in the list
  sees each item's category name in the Category column.
- **Administrator editing another user's item**: The administrator can keep or clear the item's
  category. They cannot assign one of their own categories to it, since an item may only use its
  owner's categories (FR-011).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Categories MUST be stored as their own persistent records, independent of items, so
  one category can be assigned to many items. Each category MUST belong to exactly one user (its
  owner) and be private to that user. No user, administrators included, can see, use, or delete
  another user's categories.
- **FR-002**: Users MUST be able to create a category by providing a name of 1 to 255 characters;
  leading and trailing whitespace is trimmed before validation.
- **FR-003**: Category names MUST be unique per owner, compared case-insensitively after trimming.
  Different users MAY have categories with the same name.
- **FR-004**: The application MUST provide a Categories page, reachable from the main navigation
  for every signed-in user. It lists the user's own categories in alphabetical order, and is
  where categories are created and deleted. The item add/edit form MUST NOT create or delete
  categories; it only offers a choice among existing ones.
- **FR-005**: When adding an item, users MUST be able to choose zero or one of their own
  categories.
- **FR-006**: When editing an item, users MUST be able to set, change, or clear its category.
- **FR-007**: Category MUST be optional: an item without a category is valid in every operation
  (create, edit, view, list, delete).
- **FR-008**: The Items list MUST display a Category column showing each item's category name, or
  a visually distinct "no category" indicator when none is assigned.
- **FR-009**: Viewing a single item or the item list MUST include the item's category.
- **FR-010**: Users MUST be able to delete a category after an explicit confirmation that states
  items using it will become uncategorized. Deleting a category MUST NOT delete any item; every
  item that used it MUST become uncategorized.
- **FR-011**: An item MUST only reference a category owned by the item's owner. The system MUST
  reject any attempt to assign a category that does not exist or belongs to a different user,
  leaving the item unchanged.
- **FR-012**: Validation failures (blank, too long, duplicate, missing category) MUST show a
  user-readable message explaining what to fix.
- **FR-013**: Introducing this feature MUST NOT alter or lose any existing item; all existing items
  start uncategorized.

### Key Entities

- **Category**: A named label a user creates to group their own items. Attributes: name
  (1–255 characters, unique per owner), owner (the user who created it), creation time. One
  category can be assigned to many of its owner's items. Deleted along with its owner's account.
- **Item** (existing): Gains an optional reference to at most one Category owned by the same user.
  Removing the reference makes the item uncategorized; the item is otherwise unchanged.
- **User** (existing): Owns zero or more categories, in the same way they own items.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no categories can create a category and assign it to a new item in under
  1 minute on first attempt.
- **SC-002**: 100% of rows in the Items list display either a category name or the "no category"
  indicator, with no extra click needed to see it.
- **SC-003**: Deleting a category results in zero item losses; 100% of items that used it show as
  uncategorized the next time the list is viewed.
- **SC-004**: 100% of items that existed before the feature remain present, unchanged, and
  editable after it is introduced.
- **SC-005**: Zero cases where a user can see, assign, or delete a category owned by another user.
- **SC-006**: The Items list with the Category column loads within 2 seconds for a user with 100
  categorized items.

## Assumptions

- Each item has at most one category (the description refers to "the category" and a single
  "category column"). Multiple categories or tags per item are out of scope.
- Users are expected to have tens of categories. The Categories page and the category picker show
  up to 100 categories, the same limit the Items list uses. Paging through more is out of scope.
- Renaming a category, category colors or icons, and filtering or sorting the Items list by
  category are out of scope for this feature.
- The project owner explicitly requested that categories be kept as their own stored entity, not
  as free text on each item; FR-001 reflects this.
- "Remove the category" covers both clearing an item's category (User Story 2) and deleting a
  category entirely (User Story 3).
- Existing sign-in and permission rules for items are reused: users see and edit their own items,
  administrators see all items. Categories do not follow the administrator exception; they are
  always personal (Clarifications, Q1).
- Creating a category from inside the item form ("quick create") is out of scope (Clarifications,
  Q2) and may be added later.
- The Category column appears in the existing Items list alongside Title and Description.
