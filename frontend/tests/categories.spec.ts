import { expect, test } from "@playwright/test"
import { chooseCategory, createCategory } from "./utils/category"
import { createUser } from "./utils/privateApi"
import {
  randomCategoryName,
  randomEmail,
  randomItemTitle,
  randomPassword,
} from "./utils/random"
import { logInUser } from "./utils/user"

test("Categories page is accessible and shows correct title", async ({
  page,
}) => {
  await page.goto("/categories")
  await expect(page.getByRole("heading", { name: "Categories" })).toBeVisible()
  await expect(
    page.getByText("Create and manage your categories"),
  ).toBeVisible()
  await expect(page.getByRole("button", { name: "Add Category" })).toBeVisible()
})

test("Sidebar link navigates to the Categories page", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("link", { name: "Categories" }).click()
  await page.waitForURL("/categories")
  await expect(page.getByRole("heading", { name: "Categories" })).toBeVisible()
})

test.describe("Categories management", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test.beforeEach(async ({ page }) => {
    // Fresh user per test: categories sort alphabetically, so a shared user
    // could push new rows off the first page of the table
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)
    await page.goto("/categories")
  })

  test("Shows empty state when no categories exist", async ({ page }) => {
    await expect(
      page.getByText("You don't have any categories yet"),
    ).toBeVisible()
    await expect(
      page.getByText("Add a new category to get started"),
    ).toBeVisible()
  })

  test("Create a new category successfully", async ({ page }) => {
    const name = randomCategoryName()

    await page.getByRole("button", { name: "Add Category" }).click()
    await page.getByLabel("Name").fill(name)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Category created successfully")).toBeVisible()
    await expect(page.getByRole("cell", { name, exact: true })).toBeVisible()
    await expect(
      page.getByText("You don't have any categories yet"),
    ).not.toBeVisible()
  })

  test("Duplicate name is rejected regardless of case", async ({ page }) => {
    const name = randomCategoryName()
    await createCategory(page, name)

    await page.getByRole("button", { name: "Add Category" }).click()
    await page.getByLabel("Name").fill(name.toUpperCase())
    await page.getByRole("button", { name: "Save" }).click()

    await expect(
      page.getByText("A category with this name already exists"),
    ).toBeVisible()
  })

  test("Name is required", async ({ page }) => {
    await page.getByRole("button", { name: "Add Category" }).click()
    await page.getByLabel("Name").fill("")
    await page.getByLabel("Name").blur()

    await expect(page.getByText("Name is required")).toBeVisible()
  })

  test("Other users don't see my categories", async ({ page, browser }) => {
    const name = randomCategoryName()
    await createCategory(page, name)

    const otherEmail = randomEmail()
    const otherPassword = randomPassword()
    await createUser({ email: otherEmail, password: otherPassword })
    const otherContext = await browser.newContext({
      storageState: { cookies: [], origins: [] },
    })
    const otherPage = await otherContext.newPage()
    await logInUser(otherPage, otherEmail, otherPassword)
    await otherPage.goto("/categories")

    await expect(
      otherPage.getByText("You don't have any categories yet"),
    ).toBeVisible()
    await expect(otherPage.getByText(name)).not.toBeVisible()
    await otherContext.close()
  })

  test.describe("Delete", () => {
    test("Delete an unused category", async ({ page }) => {
      const name = randomCategoryName()
      await createCategory(page, name)

      const row = page.getByRole("row").filter({ hasText: name })
      await row.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "Delete Category" }).click()
      await expect(
        page.getByText("Items using this category will become uncategorized."),
      ).toBeVisible()
      await page.getByRole("button", { name: "Delete" }).click()

      await expect(
        page.getByText("Category deleted successfully"),
      ).toBeVisible()
      await expect(page.getByRole("cell", { name, exact: true })).toHaveCount(0)
    })

    test("Deleting a category in use leaves its items uncategorized", async ({
      page,
    }) => {
      const name = randomCategoryName()
      const otherName = randomCategoryName()
      const title = randomItemTitle()
      await createCategory(page, name)
      await createCategory(page, otherName)

      await page.goto("/items")
      await page.getByRole("button", { name: "Add Item" }).click()
      await page.getByLabel("Title").fill(title)
      await chooseCategory(page, name)
      await page.getByRole("button", { name: "Save" }).click()
      await expect(page.getByRole("dialog")).not.toBeVisible()
      await expect(
        page.getByRole("row").filter({ hasText: title }),
      ).toContainText(name)

      await page.goto("/categories")
      const row = page.getByRole("row").filter({ hasText: name })
      await row.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "Delete Category" }).click()
      await page.getByRole("button", { name: "Delete" }).click()
      await expect(
        page.getByText("Category deleted successfully"),
      ).toBeVisible()

      await page.goto("/items")
      const itemRow = page.getByRole("row").filter({ hasText: title })
      await expect(itemRow).toContainText("No category")
      await expect(itemRow).not.toContainText(name)

      await page.getByRole("button", { name: "Add Item" }).click()
      await page.getByLabel("Category", { exact: true }).click()
      await expect(
        page.getByRole("option", { name: otherName, exact: true }),
      ).toBeVisible()
      await expect(page.getByRole("option", { name, exact: true })).toHaveCount(
        0,
      )
    })

    test("Cancel keeps the category", async ({ page }) => {
      const name = randomCategoryName()
      await createCategory(page, name)

      const row = page.getByRole("row").filter({ hasText: name })
      await row.getByRole("button").last().click()
      await page.getByRole("menuitem", { name: "Delete Category" }).click()
      await page.getByRole("button", { name: "Cancel" }).click()
      await expect(page.getByRole("dialog")).not.toBeVisible()
      // The actions menu stays open after cancelling (same as Items); close it
      await page.keyboard.press("Escape")

      await expect(page.getByRole("cell", { name, exact: true })).toBeVisible()
    })

    test("Saving an item with a category deleted meanwhile asks to choose again", async ({
      page,
    }) => {
      const name = randomCategoryName()
      await createCategory(page, name)

      await page.goto("/items")
      await page.getByRole("button", { name: "Add Item" }).click()
      await page.getByLabel("Title").fill(randomItemTitle())
      await chooseCategory(page, name)

      const other = await page.context().newPage()
      await other.goto("/categories")
      const row = other.getByRole("row").filter({ hasText: name })
      await row.getByRole("button").last().click()
      await other.getByRole("menuitem", { name: "Delete Category" }).click()
      await other.getByRole("button", { name: "Delete" }).click()
      await expect(
        other.getByText("Category deleted successfully"),
      ).toBeVisible()
      await other.close()

      await page.bringToFront()
      await page.getByRole("button", { name: "Save" }).click()

      await expect(
        page.getByText(
          "This category no longer exists. Please choose another.",
        ),
      ).toBeVisible()
      await expect(page.getByRole("dialog")).toBeVisible()
    })
  })
})
