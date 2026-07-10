"use client";

import Link from "next/link";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useOrderList } from "@/application/use-cases/useOrders";

import styles from "./page.module.css";

export default function OrdersPage() {
  const { data, isLoading, error } = useOrderList(httpClient);

  return (
    <main className={styles.main}>
      <h1>Your orders</h1>
      {isLoading ? <p>Loading...</p> : null}
      {error ? <p>{error}</p> : null}
      {data && data.items.length === 0 ? <p>You haven&apos;t placed any orders yet.</p> : null}
      <ul className={styles.list}>
        {data?.items.map((order) => (
          <li key={order.id}>
            <Link href={`/orders/${order.id}`} className={styles.orderLink}>
              <span>Order {order.id.slice(0, 8)}</span>
              <span>{order.status}</span>
              <span>${order.total}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
