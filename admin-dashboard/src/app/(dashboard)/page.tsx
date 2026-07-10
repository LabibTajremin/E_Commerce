"use client";

import Link from "next/link";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useMe } from "@/application/use-cases/useMe";

export default function DashboardHome() {
  const { data: me, isLoading, error } = useMe(httpClient);

  return (
    <section>
      <h1>Overview</h1>
      {isLoading ? <p>Loading...</p> : null}
      {error ? <p>{error}</p> : null}
      {me ? (
        <p>
          Signed in as <strong>{me.role}</strong> for tenant <code>{me.tenant_id}</code>.
        </p>
      ) : null}
      <ul>
        <li>
          <Link href="/products">Manage products</Link>
        </li>
        <li>
          <Link href="/categories">Manage categories</Link>
        </li>
        <li>
          <Link href="/orders">View orders</Link>
        </li>
        <li>
          <Link href="/branding">Customize storefront branding</Link>
        </li>
        <li>
          <Link href="/billing">Manage billing plan</Link>
        </li>
      </ul>
    </section>
  );
}
