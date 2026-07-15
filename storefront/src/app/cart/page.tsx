"use client";

import Link from "next/link";

import { httpClient } from "@/infrastructure/api/httpClient";
import { removeCartItem, updateCartItem, useCart } from "@/application/use-cases/useCart";
import { useProductCatalog } from "@/application/use-cases/useProducts";

import styles from "./page.module.css";

export default function CartPage() {
  const { data: cart, isLoading, error, refetch } = useCart(httpClient);
  const { byId, isLoading: catalogLoading } = useProductCatalog(httpClient);

  async function handleQuantityChange(productId: string, quantity: number) {
    if (quantity <= 0) {
      await removeCartItem(httpClient, productId);
    } else {
      await updateCartItem(httpClient, productId, quantity);
    }
    refetch();
  }

  async function handleRemove(productId: string) {
    await removeCartItem(httpClient, productId);
    refetch();
  }

  if (isLoading || catalogLoading) return <main className={styles.main}>Loading...</main>;
  if (error) return <main className={styles.main}>{error}</main>;
  if (!cart || cart.line_items.length === 0) {
    return (
      <main className={styles.main}>
        <h1>Your cart</h1>
        <p>Your cart is empty.</p>
        <Link href="/products">Continue shopping</Link>
      </main>
    );
  }

  let subtotal = 0;
  const rows = cart.line_items.map((item) => {
    const product = byId.get(item.product_id);
    const price = product ? Number(product.price) : 0;
    subtotal += price * item.quantity;
    return { item, product, lineTotal: price * item.quantity };
  });

  return (
    <main className={styles.main}>
      <h1>Your cart</h1>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Quantity</th>
            <th>Total</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ item, product, lineTotal }) => (
            <tr key={item.product_id}>
              <td>{product?.name ?? item.product_id}</td>
              <td>${product?.price ?? "—"}</td>
              <td>
                <input
                  type="number"
                  min={0}
                  defaultValue={item.quantity}
                  className={styles.quantityInput}
                  onBlur={(e) => handleQuantityChange(item.product_id, Number(e.target.value))}
                />
              </td>
              <td>${lineTotal.toFixed(2)}</td>
              <td>
                <button onClick={() => handleRemove(item.product_id)}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className={styles.summary}>
        <p>Subtotal: ${subtotal.toFixed(2)}</p>
        <Link href="/checkout" className={styles.checkoutButton}>
          Proceed to checkout
        </Link>
      </div>
    </main>
  );
}
