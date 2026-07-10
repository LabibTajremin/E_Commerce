"use client";

import { useState } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { ApiError } from "@/application/interfaces/ApiClient";
import { createCategory, deleteCategory, useCategoryList } from "@/application/use-cases/useCategories";
import { ListView } from "@/presentation/components/primitives/ListView";
import type { Column } from "@/presentation/components/primitives/DataTable";
import type { Category } from "@/domain/types";

import styles from "../products/page.module.css";

export default function CategoriesPage() {
  const { data: categories, isLoading, error, refetch } = useCategoryList(httpClient);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await createCategory(httpClient, { name });
      setName("");
      refetch();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create category");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(category: Category, event: React.MouseEvent) {
    event.stopPropagation();
    if (!window.confirm(`Delete "${category.name}"?`)) return;
    await deleteCategory(httpClient, category.id);
    refetch();
  }

  const columns: Column<Category>[] = [
    { key: "name", header: "Name" },
    { key: "slug", header: "Slug" },
    {
      key: "actions",
      header: "",
      render: (c) => (
        <button className={styles.danger} onClick={(e) => handleDelete(c, e)}>
          Delete
        </button>
      ),
    },
  ];

  return (
    <ListView
      title="Categories"
      columns={columns}
      rows={categories ?? []}
      getRowId={(c) => c.id}
      isLoading={isLoading}
      error={error}
      emptyMessage="No categories yet"
      actions={
        <form onSubmit={handleCreate} style={{ display: "flex", gap: 8 }}>
          <input
            className={styles.search}
            placeholder="New category name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <button className={styles.newButton} type="submit" disabled={isSubmitting}>
            Add
          </button>
          {formError ? <span style={{ color: "var(--color-danger)" }}>{formError}</span> : null}
        </form>
      }
    />
  );
}
