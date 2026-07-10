"use client";

import { useMemo } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Product, ProductPage } from "@/domain/types";

/** Cart line items only carry product_id/quantity; this loads the full
 * (small-store-scale) catalog once so cart/checkout pages can resolve
 * names/prices/images client-side without a public "get product by id"
 * endpoint (the backend only exposes lookup by slug). */
export function useProductCatalog(client: ApiClient) {
  const { data, isLoading, error } = useAsync<ProductPage>(
    () => client.get<ProductPage>("/api/v1/storefront/products?limit=200"),
    [client],
  );

  const byId = useMemo(() => {
    const map = new Map<string, Product>();
    for (const product of data?.items ?? []) {
      map.set(product.id, product);
    }
    return map;
  }, [data]);

  return { products: data?.items ?? [], byId, isLoading, error };
}
