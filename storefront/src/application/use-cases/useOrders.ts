"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Order, OrderPage } from "@/domain/types";

export function useOrderList(client: ApiClient) {
  return useAsync<OrderPage>(() => client.get<OrderPage>("/api/v1/storefront/orders"), [client]);
}

export function useOrder(client: ApiClient, orderId: string) {
  return useAsync<Order>(
    () => client.get<Order>(`/api/v1/storefront/orders/${orderId}`),
    [client, orderId],
  );
}
