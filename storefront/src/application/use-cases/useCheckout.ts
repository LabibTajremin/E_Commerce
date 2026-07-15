"use client";

import type { ApiClient } from "@/application/interfaces/ApiClient";
import type { Order, ShippingAddress } from "@/domain/types";

export async function checkout(client: ApiClient, shippingAddress: ShippingAddress): Promise<Order> {
  return client.post<Order>("/api/v1/storefront/checkout", { shipping_address: shippingAddress });
}

export async function payOrder(
  client: ApiClient,
  orderId: string,
  successUrl: string,
  cancelUrl: string,
): Promise<{ checkout_url: string }> {
  return client.post<{ checkout_url: string }>(`/api/v1/storefront/orders/${orderId}/pay`, {
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
}
