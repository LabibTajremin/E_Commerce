"use client";

import Link from "next/link";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useCart } from "@/application/use-cases/useCart";
import { useCustomerAuth } from "@/application/use-cases/useCustomerAuth";
import type { StoreSettings } from "@/domain/types";

import styles from "./Header.module.css";

export function Header({ settings }: { settings: StoreSettings }) {
  const { data: cart } = useCart(httpClient);
  const { isAuthenticated, logout } = useCustomerAuth();
  const itemCount = cart?.line_items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <header className={styles.header}>
      {settings.announcement_bar_text ? (
        <div className={styles.announcement}>{settings.announcement_bar_text}</div>
      ) : null}
      <div className={styles.bar}>
        <Link href="/" className={styles.brand}>
          {settings.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={settings.logo_url} alt={settings.store_name} className={styles.logo} />
          ) : null}
          <span>{settings.store_name}</span>
        </Link>
        <nav className={styles.nav}>
          <Link href="/products">Shop</Link>
          {isAuthenticated ? (
            <>
              <Link href="/orders">Orders</Link>
              <button className={styles.linkButton} onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login">Sign in</Link>
          )}
          <Link href="/cart" className={styles.cartLink}>
            Cart {itemCount > 0 ? `(${itemCount})` : ""}
          </Link>
        </nav>
      </div>
    </header>
  );
}
