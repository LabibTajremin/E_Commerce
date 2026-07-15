import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { addCartItem, useCart } from "@/application/use-cases/useCart";
import type { Cart } from "@/domain/types";

import { fakeApiClient } from "./fakeApiClient";

const emptyCart: Cart = { id: "cart-1", line_items: [] };
const oneItemCart: Cart = { id: "cart-1", line_items: [{ product_id: "p1", quantity: 1 }] };

describe("useCart", () => {
  it("loads the current cart", async () => {
    const get = vi.fn().mockResolvedValue(emptyCart);
    const client = fakeApiClient({ get });
    const { result } = renderHook(() => useCart(client));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual(emptyCart);
  });

  it("refetches when a cart:updated event fires (e.g. after addCartItem elsewhere)", async () => {
    const get = vi.fn().mockResolvedValueOnce(emptyCart).mockResolvedValueOnce(oneItemCart);
    const post = vi.fn().mockResolvedValue(oneItemCart);
    const client = fakeApiClient({ get, post });

    const { result } = renderHook(() => useCart(client));
    await waitFor(() => expect(result.current.data).toEqual(emptyCart));

    await addCartItem(client, "p1", 1);

    await waitFor(() => expect(result.current.data).toEqual(oneItemCart));
    expect(get).toHaveBeenCalledTimes(2);
  });
});
