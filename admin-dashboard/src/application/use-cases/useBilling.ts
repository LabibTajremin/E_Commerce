"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import { useAsync } from "@/application/use-cases/useAsync";
import type { SubscriptionPlan, TenantSubscription } from "@/domain/types";

export function usePlans(client: ApiClient) {
  return useAsync<SubscriptionPlan[]>(
    () => client.get<SubscriptionPlan[]>("/api/v1/admin/billing/plans"),
    [client],
  );
}

export function useSubscription(client: ApiClient) {
  return useAsync<TenantSubscription | null>(async () => {
    try {
      return await client.get<TenantSubscription>("/api/v1/admin/billing/subscription");
    } catch {
      return null;
    }
  }, [client]);
}

export async function subscribeToPlan(
  client: ApiClient,
  planId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  return client.post<{ checkout_url: string }>("/api/v1/admin/billing/subscribe", {
    plan_id: planId,
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
}
