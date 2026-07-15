"use client";

import { useState } from "react";

import { httpClient } from "@/infrastructure/api/httpClient";
import { addCartItem } from "@/application/use-cases/useCart";
import { ApiError } from "@/application/interfaces/ApiClient";

import styles from "./AddToCartButton.module.css";

export function AddToCartButton({ productId, inStock }: { productId: string; inStock: boolean }) {
  const [quantity, setQuantity] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState(false);

  async function handleAdd() {
    setError(null);
    setIsSubmitting(true);
    try {
      await addCartItem(httpClient, productId, quantity);
      setAdded(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add to cart");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!inStock) {
    return <p className={styles.outOfStock}>Out of stock</p>;
  }

  return (
    <div className={styles.wrapper}>
      <input
        type="number"
        min={1}
        value={quantity}
        onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
        className={styles.quantity}
      />
      <button className={styles.addButton} onClick={handleAdd} disabled={isSubmitting}>
        {isSubmitting ? "Adding..." : added ? "Added!" : "Add to cart"}
      </button>
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
}
