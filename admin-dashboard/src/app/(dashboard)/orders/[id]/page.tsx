"use client";

import { use, useState } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { updateOrderStatus, useOrder } from "@/application/use-cases/useOrders";
import type { OrderStatus } from "@/domain/types";

import styles from "./page.module.css";

const STATUSES: OrderStatus[] = ["pending", "paid", "fulfilled", "cancelled", "refunded"];

export default function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: order, isLoading, error, refetch } = useOrder(httpClient, id);
  const [nextStatus, setNextStatus] = useState<OrderStatus>("pending");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleStatusChange() {
    setIsSubmitting(true);
    try {
      await updateOrderStatus(httpClient, id, nextStatus);
      refetch();
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>{error}</p>;
  if (!order) return null;

  return (
    <section>
      <h1>Order {order.id.slice(0, 8)}</h1>
      <div className={styles.card}>
        <div className={styles.row}>
          <span>Status</span>
          <strong>{order.status}</strong>
        </div>
        <div className={styles.row}>
          <span>Payment status</span>
          <strong>{order.payment_status}</strong>
        </div>
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
          <span>Total</span>
          <strong>${order.total}</strong>
        </div>
      </div>

      <div className={styles.statusForm}>
        <select value={nextStatus} onChange={(e) => setNextStatus(e.target.value as OrderStatus)}>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
        <button onClick={handleStatusChange} disabled={isSubmitting}>
          Update status
        </button>
      </div>
    </section>
  );
}
