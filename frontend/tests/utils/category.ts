import { expect, type Page } from "@playwright/test"

export async function createCategory(page: Page, name: string) {
  await page.goto("/categories")
  await page.getByRole("button", { name: "Add Category" }).click()
  await page.getByLabel("Name").fill(name)
  await page.getByRole("button", { name: "Save" }).click()
  await expect(page.getByRole("dialog")).not.toBeVisible()
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible()
}

export async function chooseCategory(page: Page, name: string) {
  await page.getByLabel("Category", { exact: true }).click()
  await page.getByRole("option", { name, exact: true }).click()
}
