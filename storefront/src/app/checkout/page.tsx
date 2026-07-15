"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useCustomerAuth } from "@/application/use-cases/useCustomerAuth";
import { useCart } from "@/application/use-cases/useCart";
import { checkout } from "@/application/use-cases/useCheckout";
import { ApiError } from "@/application/interfaces/ApiClient";
import type { ShippingAddress } from "@/domain/types";

import styles from "./page.module.css";

const EMPTY_ADDRESS: ShippingAddress = {
  line1: "",
  line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
};

export default function CheckoutPage() {
  const { isAuthenticated, isLoading } = useCustomerAuth();
  const { data: cart } = useCart(httpClient);
  const router = useRouter();
  const [address, setAddress] = useState<ShippingAddress>(EMPTY_ADDRESS);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const order = await checkout(httpClient, address);
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not place order");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return <main className={styles.main}>Loading...</main>;

  if (!isAuthenticated) {
    return (
      <main className={styles.main}>
        <h1>Checkout</h1>
        <p>Sign in or create an account to complete your order.</p>
        <div className={styles.authLinks}>
          <Link href="/login" className={styles.button}>
            Sign in
          </Link>
          <Link href="/register" className={styles.button}>
            Create account
          </Link>
        </div>
      </main>
    );
  }

  if (!cart || cart.line_items.length === 0) {
    return (
      <main className={styles.main}>
        <h1>Checkout</h1>
        <p>Your cart is empty.</p>
        <Link href="/products">Continue shopping</Link>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <h1>Checkout</h1>
      <form className={styles.form} onSubmit={handleSubmit}>
        <label>
          Address line 1
          <input
            required
            value={address.line1}
            onChange={(e) => setAddress({ ...address, line1: e.target.value })}
          />
        </label>
        <label>
          Address line 2 (optional)
          <input
            value={address.line2 ?? ""}
            onChange={(e) => setAddress({ ...address, line2: e.target.value })}
          />
        </label>
        <label>
          City
          <input
            required
            value={address.city}
            onChange={(e) => setAddress({ ...address, city: e.target.value })}
          />
        </label>
        <label>
          State
          <input
            required
            value={address.state}
            onChange={(e) => setAddress({ ...address, state: e.target.value })}
          />
        </label>
        <label>
          Postal code
          <input
            required
            value={address.postal_code}
            onChange={(e) => setAddress({ ...address, postal_code: e.target.value })}
          />
        </label>
        <label>
          Country
          <input
            required
            value={address.country}
            onChange={(e) => setAddress({ ...address, country: e.target.value })}
          />
        </label>
        {error ? <p className={styles.error}>{error}</p> : null}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Placing order..." : "Place order"}
        </button>
      </form>
    </main>
  );
}
