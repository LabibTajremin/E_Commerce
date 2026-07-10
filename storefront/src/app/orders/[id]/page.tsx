"use client";

import { use, useState } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useOrder } from "@/application/use-cases/useOrders";
import { payOrder } from "@/application/use-cases/useCheckout";
import { ApiError } from "@/application/interfaces/ApiClient";

import styles from "./page.module.css";

export default function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: order, isLoading, error } = useOrder(httpClient, id);
  const [payError, setPayError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);

  async function handlePay() {
    setPayError(null);
    setIsPaying(true);
    try {
      const { checkout_url } = await payOrder(
        httpClient,
        id,
        `${window.location.origin}/orders/${id}?paid=1`,
        `${window.location.origin}/orders/${id}?canceled=1`,
      );
      window.location.href = checkout_url;
    } catch (err) {
      setPayError(err instanceof ApiError ? err.message : "Could not start payment");
      setIsPaying(false);
    }
  }

  if (isLoading) return <main className={styles.main}>Loading...</main>;
  if (error) return <main className={styles.main}>{error}</main>;
  if (!order) return null;

  return (
    <main className={styles.main}>
      <h1>Order {order.id.slice(0, 8)}</h1>
      <p className={styles.status}>
        Status: <strong>{order.status}</strong>
      </p>
      <div className={styles.card}>
        {order.line_items.map((item) => (
          <div className={styles.row} key={item.product_id}>
            <span>
              {item.product_name} x{item.quantity}
            </span>
            <span>${item.line_total}</span>
          </div>
        ))}
        <div className={styles.row}>
          <span>Subtotal</span>
          <span>${order.subtotal}</span>
        </div>
        <div className={styles.row}>
          <span>Tax</span>
          <span>${order.tax}</span>
        </div>
        <div className={styles.row}>
          <span>Shipping</span>
          <span>${order.shipping}</span>
        </div>
        <div className={styles.row}>
          <strong>Total</strong>
          <strong>${order.total}</strong>
        </div>
      </div>

      {order.status === "pending" ? (
        <div>
          <button className={styles.payButton} onClick={handlePay} disabled={isPaying}>
            {isPaying ? "Redirecting..." : "Pay now"}
          </button>
          {payError ? <p className={styles.error}>{payError}</p> : null}
        </div>
      ) : null}
    </main>
  );
}
