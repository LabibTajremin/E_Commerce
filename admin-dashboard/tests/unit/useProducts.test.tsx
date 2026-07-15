import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useProductList } from "@/application/use-cases/useProducts";
import type { ProductPage } from "@/domain/types";

import { fakeApiClient } from "./fakeApiClient";

const page: ProductPage = {
  items: [
    {
      id: "1",
      tenant_id: "t1",
      name: "Widget",
      slug: "widget",
      description: null,
      price: "9.99",
      compare_at_price: null,
      sku: null,
      images: [],
      stock_qty: 5,
      status: "draft",
      category_id: null,
    },
  ],
  total: 1,
};

describe("useProductList", () => {
  it("loads the first page and exposes items/total", async () => {
    const get = vi.fn().mockResolvedValue(page);
    const client = fakeApiClient({ get });

    const { result } = renderHook(() => useProductList(client, ""));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.products).toEqual(page.items);
    expect(result.current.total).toBe(1);
    expect(get).toHaveBeenCalledWith(expect.stringContaining("limit=20"));
    expect(get).toHaveBeenCalledWith(expect.stringContaining("offset=0"));
  });

  it("includes the search term as a query param when set", async () => {
    const get = vi.fn().mockResolvedValue(page);
    const client = fakeApiClient({ get });

    renderHook(() => useProductList(client, "widget"));

    await waitFor(() =>
      expect(get).toHaveBeenCalledWith(expect.stringContaining("search=widget")),
    );
  });

  it("surfaces the error message when the request fails", async () => {
    const client = fakeApiClient({
      get: vi.fn().mockRejectedValue(new Error("boom")),
    });

    const { result } = renderHook(() => useProductList(client, ""));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Something went wrong");
  });
});
