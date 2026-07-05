"use client";

import { httpClient } from "@/infrastructure/api/httpClient";
import { useHealthCheck } from "@/application/use-cases/useHealthCheck";

export default function Home() {
  const status = useHealthCheck(httpClient);

  return (
    <main>
      <h1>Admin Dashboard</h1>
      <p>API status: {status}</p>
    </main>
  );
}
