import type { ColumnDef } from "@tanstack/react-table"

import type { CategoryPublic } from "@/client"
import type { DataTableFeatures } from "@/components/Common/DataTable"
import { CategoryActionsMenu } from "./CategoryActionsMenu"

export const columns: ColumnDef<DataTableFeatures, CategoryPublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => {
      const createdAt = row.original.created_at
      return (
        <span className="text-muted-foreground">
          {createdAt ? new Date(createdAt).toLocaleDateString() : "—"}
        </span>
      )
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <CategoryActionsMenu category={row.original} />
      </div>
    ),
  },
]
