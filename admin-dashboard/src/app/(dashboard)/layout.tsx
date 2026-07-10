"use client";

import type { ReactNode } from "react";

import { useAuth } from "@/application/use-cases/useAuth";
import { RequireAuth } from "@/presentation/providers/RequireAuth";
import { SideMenu, type NavItem } from "@/presentation/components/primitives/SideMenu";

import styles from "./layout.module.css";

const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/" },
  { label: "Products", href: "/products" },
  { label: "Categories", href: "/categories" },
  { label: "Orders", href: "/orders" },
  { label: "Branding", href: "/branding" },
  { label: "Billing", href: "/billing" },
];

function LogoutButton() {
  const { logout } = useAuth();
  return (
    <button className={styles.logout} onClick={() => void logout()}>
      Sign out
    </button>
  );
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className={styles.shell}>
        <aside className={styles.sidebar}>
          <div className={styles.brand}>Storefront Admin</div>
          <SideMenu items={NAV_ITEMS} footer={<LogoutButton />} />
        </aside>
        <main className={styles.content}>{children}</main>
      </div>
    </RequireAuth>
  );
}
