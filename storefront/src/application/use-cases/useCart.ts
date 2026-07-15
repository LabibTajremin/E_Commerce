"use client";

import { useEffect } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Cart } from "@/domain/types";

export const CART_UPDATED_EVENT = "cart:updated";

function notifyCartUpdated(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(CART_UPDATED_EVENT));
  }
}

export function useCart(client: ApiClient) {
  const state = useAsync<Cart>(() => client.get<Cart>("/api/v1/storefront/cart"), [client]);

  useEffect(() => {
    window.addEventListener(CART_UPDATED_EVENT, state.refetch);
    return () => window.removeEventListener(CART_UPDATED_EVENT, state.refetch);
  }, [state.refetch]);

  return state;
}

export async function addCartItem(
  client: ApiClient,
  productId: string,
  quantity: number,
): Promise<Cart> {
  const cart = await client.post<Cart>("/api/v1/storefront/cart/items", {
    product_id: productId,
    quantity,
  });
  notifyCartUpdated();
  return cart;
}

export async function updateCartItem(
  client: ApiClient,
  productId: string,
  quantity: number,
): Promise<Cart> {
  const cart = await client.put<Cart>(`/api/v1/storefront/cart/items/${productId}`, { quantity });
  notifyCartUpdated();
  return cart;
}

export async function removeCartItem(client: ApiClient, productId: string): Promise<Cart> {
  const cart = await client.delete<Cart>(`/api/v1/storefront/cart/items/${productId}`);
  notifyCartUpdated();
  return cart;
}
