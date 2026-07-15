"use client";

import { useState } from "react";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { Order, OrderPage, OrderStatus } from "@/domain/types";

const PAGE_SIZE = 20;

export function useOrderList(client: ApiClient, statusFilter: OrderStatus | "") {
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error, refetch } = useAsync<OrderPage>(() => {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (statusFilter) params.set("status", statusFilter);
    return client.get<OrderPage>(`/api/v1/admin/orders?${params.toString()}`);
  }, [client, offset, statusFilter]);

  return {
    orders: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refetch,
    offset,
    limit: PAGE_SIZE,
    nextPage: () => setOffset((o) => o + PAGE_SIZE),
    prevPage: () => setOffset((o) => Math.max(0, o - PAGE_SIZE)),
  };
}

export function useOrder(client: ApiClient, orderId: string) {
  return useAsync<Order>(() => client.get<Order>(`/api/v1/admin/orders/${orderId}`), [
    client,
    orderId,
  ]);
}

export async function updateOrderStatus(
  client: ApiClient,
  orderId: string,
  status: OrderStatus,
): Promise<Order> {
  return client.patch<Order>(`/api/v1/admin/orders/${orderId}/status`, { status });
}
