import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AxiosError } from "axios"

import { CategoriesService, type CategoryPublic } from "@/client"
import { FormControl, FormDescription } from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// Radix Select items can't use "" as a value, so "No category" uses a sentinel
const NO_CATEGORY = "none"

export const STALE_CATEGORY_MESSAGE =
  "This category no longer exists. Please choose another."

export const isStaleCategoryError = (err: Error): boolean =>
  err instanceof AxiosError &&
  err.response?.status === 400 &&
  (err.response.data as { detail?: unknown } | undefined)?.detail ===
    "Category not found"

interface CategorySelectProps {
  value: string | null
  onChange: (value: string | null) => void
  currentCategory?: CategoryPublic | null
  // An item may only use its owner's categories, so admins editing someone
  // else's item can only keep or clear the current one
  ownedByCurrentUser?: boolean
  disabled?: boolean
}

// Must be rendered inside a FormItem so the label targets the trigger
const CategorySelect = ({
  value,
  onChange,
  currentCategory,
  ownedByCurrentUser = true,
  disabled = false,
}: CategorySelectProps) => {
  const { data, isPending } = useQuery({
    queryKey: ["categories"],
    queryFn: async () =>
      (
        await CategoriesService.readCategories({
          query: { skip: 0, limit: 100 },
        })
      ).data,
    enabled: ownedByCurrentUser,
  })

  const options = ownedByCurrentUser
    ? (data?.data ?? [])
    : currentCategory
      ? [currentCategory]
      : []
  const hasNoCategories =
    ownedByCurrentUser && !isPending && options.length === 0

  return (
    <>
      <Select
        value={value ?? NO_CATEGORY}
        onValueChange={(selected) =>
          onChange(selected === NO_CATEGORY ? null : selected)
        }
        disabled={disabled || hasNoCategories}
      >
        <FormControl>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="No category" />
          </SelectTrigger>
        </FormControl>
        <SelectContent>
          <SelectItem value={NO_CATEGORY}>No category</SelectItem>
          {options.map((category) => (
            <SelectItem key={category.id} value={category.id}>
              {category.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {hasNoCategories && (
        <FormDescription>
          No categories yet. Create one on the{" "}
          <Link to="/categories" className="underline underline-offset-4">
            Categories page
          </Link>
          .
        </FormDescription>
      )}
    </>
  )
}

export default CategorySelect
