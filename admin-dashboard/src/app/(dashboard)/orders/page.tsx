"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useOrderList } from "@/application/use-cases/useOrders";
import { ListView } from "@/presentation/components/primitives/ListView";
import type { Column } from "@/presentation/components/primitives/DataTable";
import type { Order, OrderStatus } from "@/domain/types";

import styles from "../products/page.module.css";

const STATUS_OPTIONS: (OrderStatus | "")[] = [
  "",
  "pending",
  "paid",
  "fulfilled",
  "cancelled",
  "refunded",
];

export default function OrdersPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">("");
  const { orders, total, isLoading, error, offset, limit, nextPage, prevPage } = useOrderList(
    httpClient,
    statusFilter,
  );

  const columns: Column<Order>[] = [
    { key: "id", header: "Order", render: (o) => o.id.slice(0, 8) },
    { key: "status", header: "Status" },
    { key: "payment_status", header: "Payment" },
    { key: "total", header: "Total", render: (o) => `$${o.total}` },
  ];

  return (
    <ListView
      title="Orders"
      columns={columns}
      rows={orders}
      getRowId={(o) => o.id}
      onRowClick={(o) => router.push(`/orders/${o.id}`)}
      isLoading={isLoading}
      error={error}
      emptyMessage="No orders yet"
      actions={
        <select
          className={styles.search}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as OrderStatus | "")}
        >
          {STATUS_OPTIONS.map((status) => (
            <option key={status || "all"} value={status}>
              {status || "All statuses"}
            </option>
          ))}
        </select>
      }
      pagination={{ offset, limit, total, onPrev: prevPage, onNext: nextPage }}
    />
  );
}
