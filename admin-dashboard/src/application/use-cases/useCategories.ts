"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Category, CategoryInput } from "@/domain/types";

export function useCategoryList(client: ApiClient) {
  return useAsync<Category[]>(
    () => client.get<Category[]>("/api/v1/admin/categories"),
    [client],
  );
}

export async function createCategory(client: ApiClient, input: CategoryInput): Promise<Category> {
  return client.post<Category>("/api/v1/admin/categories", input);
}

export async function deleteCategory(client: ApiClient, categoryId: string): Promise<void> {
  await client.delete(`/api/v1/admin/categories/${categoryId}`);
}
