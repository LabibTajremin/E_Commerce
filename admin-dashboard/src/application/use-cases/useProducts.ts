"use client";

import { useState } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Product, ProductInput, ProductPage } from "@/domain/types";

const PAGE_SIZE = 20;

export function useProductList(client: ApiClient, search: string) {
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error, refetch } = useAsync<ProductPage>(() => {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (search) params.set("search", search);
    return client.get<ProductPage>(`/api/v1/admin/products?${params.toString()}`);
  }, [client, offset, search]);

  return {
    products: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refetch,
    offset,
    limit: PAGE_SIZE,
    nextPage: () => setOffset((o) => o + PAGE_SIZE),
    prevPage: () => setOffset((o) => Math.max(0, o - PAGE_SIZE)),
    resetPage: () => setOffset(0),
  };
}

export function useProduct(client: ApiClient, productId: string) {
  return useAsync<Product>(
    () => client.get<Product>(`/api/v1/admin/products/${productId}`),
    [client, productId],
  );
}

export async function createProduct(client: ApiClient, input: ProductInput): Promise<Product> {
  return client.post<Product>("/api/v1/admin/products", input);
}

export async function updateProduct(
  client: ApiClient,
  productId: string,
  input: Partial<ProductInput>,
): Promise<Product> {
  return client.patch<Product>(`/api/v1/admin/products/${productId}`, input);
}

export async function deleteProduct(client: ApiClient, productId: string): Promise<void> {
  await client.delete(`/api/v1/admin/products/${productId}`);
}

export async function publishProducts(client: ApiClient, productIds: string[]): Promise<void> {
  await client.post("/api/v1/admin/products/bulk-status", {
    product_ids: productIds,
    status: "published",
  });
}
