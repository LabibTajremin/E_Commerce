"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { httpClient } from "@/infrastructure/api/httpClient";
import {
  deleteProduct,
  publishProducts,
  useProductList,
} from "@/application/use-cases/useProducts";
import { ListView } from "@/presentation/components/primitives/ListView";
import type { Column } from "@/presentation/components/primitives/DataTable";
import type { Product } from "@/domain/types";

import styles from "./page.module.css";

export default function ProductsPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const {
    products,
    total,
    isLoading,
    error,
    refetch,
    offset,
    limit,
    nextPage,
    prevPage,
  } = useProductList(httpClient, search);

  async function handlePublish(product: Product, event: React.MouseEvent) {
    event.stopPropagation();
    await publishProducts(httpClient, [product.id]);
    refetch();
  }

  async function handleDelete(product: Product, event: React.MouseEvent) {
    event.stopPropagation();
    if (!window.confirm(`Delete "${product.name}"?`)) return;
    await deleteProduct(httpClient, product.id);
    refetch();
  }

  const columns: Column<Product>[] = [
    { key: "name", header: "Name" },
    { key: "price", header: "Price", render: (p) => `$${p.price}` },
    { key: "stock_qty", header: "Stock" },
    {
      key: "status",
      header: "Status",
      render: (p) => <span className={styles[p.status]}>{p.status}</span>,
    },
    {
      key: "actions",
      header: "",
      render: (p) => (
        <div className={styles.rowActions}>
          {p.status === "draft" ? (
            <button onClick={(e) => handlePublish(p, e)}>Publish</button>
          ) : null}
          <button className={styles.danger} onClick={(e) => handleDelete(p, e)}>
            Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <ListView
      title="Products"
      columns={columns}
      rows={products}
      getRowId={(p) => p.id}
      onRowClick={(p) => router.push(`/products/${p.id}`)}
      isLoading={isLoading}
      error={error}
      emptyMessage="No products yet"
      actions={
        <>
          <input
            className={styles.search}
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Link className={styles.newButton} href="/products/new">
            New product
          </Link>
        </>
      }
      pagination={{ offset, limit, total, onPrev: prevPage, onNext: nextPage }}
    />
  );
}
